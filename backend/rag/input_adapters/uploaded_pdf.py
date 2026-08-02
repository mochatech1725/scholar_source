"""Normalize authenticated, user-scoped PDF uploads into learning context."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.models import CourseInputRequest
from backend.rag.config import RagSettings
from backend.rag.errors import UploadedPdfNormalizationError
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.input_adapters.url_page import LearningOutlineDeriver
from backend.rag.models import (
    FieldProvenance,
    LearningConstraints,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
)
from backend.uploads import UPLOAD_ROOT, normalize_upload_id

UPLOAD_CONTEXT_WARNING = (
    "The uploaded book was used only to derive learning context and is not an approved recommendation."
)


@dataclass(frozen=True, slots=True)
class ExtractedUploadedPdf:
    """Text extracted in page order with non-empty source page numbers."""

    text: str
    page_numbers: tuple[int, ...]
    total_pages: int

    @property
    def skipped_page_count(self) -> int:
        """Return pages that did not contain enough useful extracted text."""

        return self.total_pages - len(self.page_numbers)


class UploadedPdfAdapter:
    """Validate and normalize a PDF already resolved for its authenticated owner."""

    def __init__(self, *, settings: RagSettings, outline_deriver: LearningOutlineDeriver) -> None:
        self._settings = settings
        self._outline_deriver = outline_deriver
        self._method = f"uploaded_pdf_adapter:{settings.uploaded_pdf_adapter_version}"
        self._outline_method = f"structured_outline:{settings.learning_outline_prompt_version}"

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Return a traceable learning request from one owned local upload."""

        upload_id, pdf_path = _validated_upload_reference(request)
        extracted = _extract_uploaded_pdf(pdf_path, self._settings)
        page_reference = _page_reference(upload_id, extracted.page_numbers)
        try:
            outline = self._outline_deriver.derive(
                text=extracted.text,
                source_url=page_reference,
                media_type="pdf",
            )
        except Exception as error:  # noqa: BLE001 - model/provider boundary becomes a domain error
            raise UploadedPdfNormalizationError(
                "outline_derivation_failed",
                f"Could not derive a structured learning outline from the uploaded PDF: {error}",
            ) from error

        title = request.book_title or request.textbook or outline.title
        author = request.book_author or outline.author
        subject = request.subject or outline.subject
        chapters = _merge_values([request.chapter] if request.chapter else [], outline.chapters)
        sections = _merge_values(_split_values(request.sections), outline.sections)
        constraints = _constraints_from(request)
        provenance = {
            NormalizedLearningField.CANONICAL_IDENTIFIER: FieldProvenance(
                origin=ProvenanceOrigin.ADAPTER_DERIVED,
                source_reference=f"upload:{upload_id}",
                method=self._method,
                confidence=1.0,
            ),
            NormalizedLearningField.TOPICS: self._page_provenance(page_reference, outline.confidence),
        }
        values = {
            NormalizedLearningField.TITLE: (title, request.book_title or request.textbook),
            NormalizedLearningField.AUTHOR: (author, request.book_author),
            NormalizedLearningField.SUBJECT: (subject, request.subject),
            NormalizedLearningField.CHAPTERS: (chapters, request.chapter),
            NormalizedLearningField.SECTIONS: (sections, request.sections),
        }
        for field, (value, supplied) in values.items():
            if value:
                provenance[field] = self._field_provenance(field, supplied, page_reference, outline.confidence)
        if constraints != LearningConstraints():
            provenance[NormalizedLearningField.USER_CONSTRAINTS] = FieldProvenance(
                origin=ProvenanceOrigin.USER_INPUT,
                source_reference=InputSourceReference.RESOURCE_PREFERENCES,
                method=self._method,
                confidence=1.0,
            )

        warnings = [*outline.warnings, UPLOAD_CONTEXT_WARNING]
        if extracted.skipped_page_count:
            warnings.append(_mixed_pdf_warning(extracted))

        return NormalizedLearningRequest(
            input_kind=LearningInputKind.UPLOADED_PDF,
            canonical_identifier=f"upload:{upload_id}",
            title=title,
            author=author,
            subject=subject,
            topics=_merge_values(outline.topics, []),
            chapters=chapters,
            sections=sections,
            user_constraints=constraints,
            field_provenance=provenance,
            warnings=warnings,
            confidence=outline.confidence,
        )

    def _page_provenance(self, reference: str, confidence: float) -> FieldProvenance:
        return FieldProvenance(
            origin=ProvenanceOrigin.EXTRACTED_CONTENT,
            source_reference=reference,
            method=self._outline_method,
            confidence=confidence,
        )

    def _field_provenance(
        self,
        field: NormalizedLearningField,
        supplied: object,
        page_reference: str,
        confidence: float,
    ) -> FieldProvenance:
        references = {
            NormalizedLearningField.TITLE: InputSourceReference.BOOK_TITLE,
            NormalizedLearningField.AUTHOR: InputSourceReference.BOOK_AUTHOR,
            NormalizedLearningField.SUBJECT: InputSourceReference.SUBJECT,
            NormalizedLearningField.CHAPTERS: InputSourceReference.CHAPTER,
            NormalizedLearningField.SECTIONS: InputSourceReference.SECTIONS,
        }
        if supplied:
            return FieldProvenance(
                origin=ProvenanceOrigin.USER_INPUT,
                source_reference=references[field],
                method=self._method,
                confidence=1.0,
            )
        return self._page_provenance(page_reference, confidence)


def _validated_upload_reference(request: CourseInputRequest) -> tuple[str, Path]:
    if not request.book_upload_id or not request.book_pdf_path:
        raise UploadedPdfNormalizationError(
            "upload_not_resolved",
            "Uploaded-PDF input requires an authenticated, user-owned upload resolved to an internal path.",
        )
    upload_id = normalize_upload_id(request.book_upload_id)
    pdf_path = Path(request.book_pdf_path).resolve()
    upload_root = UPLOAD_ROOT.resolve()
    try:
        relative_path = pdf_path.relative_to(upload_root)
    except ValueError as error:
        raise UploadedPdfNormalizationError(
            "upload_ownership_invalid",
            "Uploaded PDF is outside owned storage.",
        ) from error
    if len(relative_path.parts) != 2 or relative_path.name != f"{upload_id}.pdf":
        raise UploadedPdfNormalizationError(
            "upload_ownership_invalid",
            "Uploaded PDF path does not match the authenticated upload reference.",
        )
    if not pdf_path.is_file():
        raise UploadedPdfNormalizationError("upload_not_found", "Uploaded PDF was not found.")
    return upload_id, pdf_path


def _extract_uploaded_pdf(pdf_path: Path, settings: RagSettings) -> ExtractedUploadedPdf:
    try:
        size = pdf_path.stat().st_size
    except OSError as error:
        raise UploadedPdfNormalizationError("upload_unreadable", "Uploaded PDF could not be read.") from error
    if size > settings.max_upload_pdf_bytes:
        raise UploadedPdfNormalizationError(
            "file_too_large",
            f"Uploaded PDF exceeds {settings.max_upload_pdf_bytes} bytes.",
        )
    try:
        with pdf_path.open("rb") as pdf_file:
            if pdf_file.read(5) != b"%PDF-":
                raise UploadedPdfNormalizationError("invalid_file_type", "Uploaded file is not a PDF.")
            pdf_file.seek(0)
            reader = PdfReader(pdf_file)
            if reader.is_encrypted and reader.decrypt("") == 0:
                raise UploadedPdfNormalizationError("encrypted_pdf", "Encrypted PDFs are not supported.")
            total_pages = len(reader.pages)
            pages: list[str] = []
            page_numbers: list[int] = []
            extracted_character_count = 0
            usable_character_count = 0
            for page_number, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                extracted_character_count += len(text)
                if len(text) >= settings.uploaded_pdf_min_page_chars:
                    pages.append(f"[Page {page_number}]\n{text}")
                    page_numbers.append(page_number)
                    usable_character_count += len(text)
    except UploadedPdfNormalizationError:
        raise
    except (OSError, PdfReadError, ValueError) as error:
        raise UploadedPdfNormalizationError("corrupt_pdf", "Uploaded PDF is corrupt or unreadable.") from error
    if extracted_character_count == 0:
        raise UploadedPdfNormalizationError(
            "ocr_required",
            "Uploaded PDF contains no extractable text. OCR is not configured.",
        )
    minimum_text_pages = min(total_pages, settings.uploaded_pdf_min_text_pages)
    text_page_ratio = len(page_numbers) / total_pages if total_pages else 0.0
    if (
        usable_character_count < settings.uploaded_pdf_min_total_chars
        or len(page_numbers) < minimum_text_pages
        or text_page_ratio < settings.uploaded_pdf_min_text_page_ratio
    ):
        raise UploadedPdfNormalizationError(
            "insufficient_extractable_text",
            (
                "Uploaded PDF does not contain enough extractable text for a reliable learning outline. "
                "OCR is not configured."
            ),
        )
    return ExtractedUploadedPdf(
        text="\n\n".join(pages),
        page_numbers=tuple(page_numbers),
        total_pages=total_pages,
    )


def _mixed_pdf_warning(extracted: ExtractedUploadedPdf) -> str:
    return (
        f"Text could not be extracted reliably from {extracted.skipped_page_count} of "
        f"{extracted.total_pages} pages; the learning outline may be incomplete."
    )


def _page_reference(upload_id: str, pages: tuple[int, ...]) -> str:
    return f"upload:{upload_id}#pages={','.join(str(page) for page in pages)}"


def _constraints_from(request: CourseInputRequest) -> LearningConstraints:
    return LearningConstraints(
        desired_resource_types=list(request.desired_resource_types or []),
        excluded_sites=_split_values(request.excluded_sites),
        targeted_sites=_split_values(request.targeted_sites),
        preferred_creators=_split_values(request.preferred_creators),
    )


def _split_values(value: str | None) -> list[str]:
    return _merge_values((part.strip() for part in value.split(",")), []) if value else []


def _merge_values(first: Iterable[str], second: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in (*first, *second):
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            result.append(normalized)
            seen.add(key)
    return result
