"""Normalize submitted book URLs as learning context, not recommendations."""

from __future__ import annotations

from collections.abc import Iterable

from backend.models import CourseInputRequest
from backend.rag.config import RagSettings
from backend.rag.errors import InputNormalizationError
from backend.rag.extraction.extractor import SourceExtractor
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.input_adapters.text_budget import apply_text_budget
from backend.rag.input_adapters.url_page import LearningOutlineDeriver
from backend.rag.models import (
    FieldProvenance,
    LearningConstraints,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
)
from backend.rag.sources.policy import normalize_url

BOOK_CONTEXT_WARNING = (
    "The submitted book was used only to derive learning context. It is not an approved recommendation and may be "
    "cited only if it separately passes source-quality checks."
)
DIRECT_PDF_WARNING = "The submitted book URL resolved directly to a PDF."


class BookUrlAdapter:
    """Normalize catalog, publisher, readable-book, and direct-PDF URLs."""

    def __init__(
        self,
        *,
        settings: RagSettings,
        extractor: SourceExtractor,
        outline_deriver: LearningOutlineDeriver,
    ) -> None:
        self._extractor = extractor
        self._outline_deriver = outline_deriver
        self._budget_chars = settings.max_outline_input_chars
        self._method = f"book_url_adapter:{settings.book_url_adapter_version}"
        self._outline_method = f"structured_outline:{settings.learning_outline_prompt_version}"

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Return traceable learning context from one validated book URL."""

        if not request.book_url:
            raise InputNormalizationError("Book-URL input requires book_url.")

        try:
            extracted = self._extractor.extract_url(request.book_url)
        except Exception as error:  # noqa: BLE001 - provider boundary becomes a domain error
            raise InputNormalizationError(f"Could not extract learning content from book URL: {error}") from error
        if not extracted.text.strip():
            raise InputNormalizationError("Book URL contained no extractable learning content.")

        budgeted = apply_text_budget(extracted.text, budget_chars=self._budget_chars)
        try:
            outline = self._outline_deriver.derive(
                text=budgeted.text,
                source_url=extracted.final_url,
                media_type=extracted.media_type,
            )
        except Exception as error:  # noqa: BLE001 - model/provider boundary becomes a domain error
            raise InputNormalizationError(f"Could not derive a structured book outline: {error}") from error

        canonical_url = normalize_url(extracted.final_url)
        title = outline.title or extracted.title
        chapters = _prepend_optional(request.chapter, outline.chapters)
        sections = _merge_values(_split_values(request.sections), outline.sections)
        constraints = _constraints_from(request)
        provenance = {
            NormalizedLearningField.CANONICAL_IDENTIFIER: FieldProvenance(
                origin=ProvenanceOrigin.ADAPTER_DERIVED,
                source_reference=canonical_url,
                method=self._method,
                confidence=1.0,
            ),
            NormalizedLearningField.TOPICS: self._outline_provenance(canonical_url, outline.confidence),
        }
        extracted_fields = {
            NormalizedLearningField.TITLE: title,
            NormalizedLearningField.AUTHOR: outline.author,
            NormalizedLearningField.SUBJECT: outline.subject,
        }
        for field, value in extracted_fields.items():
            if value:
                provenance[field] = self._outline_provenance(canonical_url, outline.confidence)
        if chapters:
            provenance[NormalizedLearningField.CHAPTERS] = self._context_provenance(
                request.chapter, InputSourceReference.CHAPTER, canonical_url, outline.confidence
            )
        if sections:
            provenance[NormalizedLearningField.SECTIONS] = self._context_provenance(
                request.sections, InputSourceReference.SECTIONS, canonical_url, outline.confidence
            )
        if constraints != LearningConstraints():
            provenance[NormalizedLearningField.USER_CONSTRAINTS] = FieldProvenance(
                origin=ProvenanceOrigin.USER_INPUT,
                source_reference=InputSourceReference.RESOURCE_PREFERENCES,
                method=self._method,
                confidence=1.0,
            )

        warnings = [*outline.warnings, BOOK_CONTEXT_WARNING]
        if budgeted.warning:
            warnings.append(budgeted.warning)
        if extracted.media_type == "pdf":
            warnings.append(DIRECT_PDF_WARNING)

        return NormalizedLearningRequest(
            input_kind=LearningInputKind.BOOK_URL,
            canonical_identifier=f"url:{canonical_url}",
            title=title,
            author=outline.author,
            subject=outline.subject,
            topics=_merge_values(outline.topics, []),
            chapters=chapters,
            sections=sections,
            user_constraints=constraints,
            field_provenance=provenance,
            warnings=warnings,
            confidence=outline.confidence,
        )

    def _outline_provenance(self, canonical_url: str, confidence: float) -> FieldProvenance:
        return FieldProvenance(
            origin=ProvenanceOrigin.EXTRACTED_CONTENT,
            source_reference=canonical_url,
            method=self._outline_method,
            confidence=confidence,
        )

    def _context_provenance(
        self,
        supplied_value: str | None,
        source_reference: InputSourceReference,
        canonical_url: str,
        confidence: float,
    ) -> FieldProvenance:
        if supplied_value:
            return FieldProvenance(
                origin=ProvenanceOrigin.USER_INPUT,
                source_reference=source_reference,
                method=self._method,
                confidence=1.0,
            )
        return self._outline_provenance(canonical_url, confidence)


def _constraints_from(request: CourseInputRequest) -> LearningConstraints:
    return LearningConstraints(
        desired_resource_types=list(request.desired_resource_types or []),
        excluded_sites=_split_values(request.excluded_sites),
        targeted_sites=_split_values(request.targeted_sites),
        preferred_creators=_split_values(request.preferred_creators),
    )


def _split_values(value: str | None) -> list[str]:
    return _merge_values((part.strip() for part in value.split(",")), []) if value else []


def _prepend_optional(value: str | None, values: list[str]) -> list[str]:
    return _merge_values([value] if value else [], values)


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
