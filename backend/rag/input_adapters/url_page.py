"""Normalize course and general educational URLs through v2 extraction."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, cast

from langchain_openai import ChatOpenAI
from pydantic import Field

from backend.models import CourseInputRequest
from backend.rag.config import RagSettings
from backend.rag.errors import InputNormalizationError
from backend.rag.extraction.extractor import ExtractedContent, SourceExtractor
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.input_adapters.text_budget import apply_text_budget
from backend.rag.models import (
    FieldProvenance,
    LearningConstraints,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
    RagModel,
)
from backend.rag.sources.policy import normalize_url

COURSE_PAGE_MARKERS = (
    "course description",
    "course overview",
    "course syllabus",
    "learning objectives",
    "learning outcomes",
    "office hours",
    "prerequisites",
    "syllabus",
)

OUTLINE_SYSTEM_PROMPT = """Derive a concise learning outline from the supplied educational content.

Rules:
- Use only the supplied extracted content. Do not add outside knowledge.
- Return the page title, author, institution, and subject only when supported.
- Topics must be specific concepts a student could search for and study.
- Preserve named chapters or sections only when the content identifies them.
- Do not treat navigation, legal notices, or promotional copy as learning topics.
- Record uncertainty in warnings and lower confidence when the outline is thin.
"""


class LearningOutline(RagModel):
    """Schema-constrained learning context derived from extracted page text."""

    title: str | None = None
    author: str | None = None
    institution: str | None = None
    subject: str | None = None
    topics: list[str] = Field(min_length=1)
    chapters: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class LearningOutlineDeriver(Protocol):
    """Versioned structured extraction boundary for unstructured page text."""

    def derive(self, *, text: str, source_url: str, media_type: str) -> LearningOutline:
        """Derive only learning context supported by the extracted text."""


class StructuredOutlineModel(Protocol):
    """Minimal interface returned by a schema-bound chat model."""

    def invoke(self, input: object) -> LearningOutline:
        """Invoke the model with page-extraction messages."""
        ...


class OutlineChatModel(Protocol):
    """Chat model capable of returning a schema-bound learning outline."""

    def with_structured_output(self, schema: type[LearningOutline]) -> object:
        """Bind the learning-outline schema to the model."""
        ...


class StructuredLearningOutlineDeriver:
    """Derive a typed learning outline from extracted content only."""

    def __init__(self, settings: RagSettings, llm: OutlineChatModel | None = None) -> None:
        base_llm = llm or ChatOpenAI(
            model=settings.chat_model,
            temperature=0.0,
            seed=settings.llm_seed,
        )
        self._structured_llm = cast(
            StructuredOutlineModel,
            base_llm.with_structured_output(LearningOutline),
        )
        self._budget_chars = settings.max_outline_input_chars

    def derive(self, *, text: str, source_url: str, media_type: str) -> LearningOutline:
        """Return a schema-constrained outline without exposing other sources."""

        if not text.strip():
            raise InputNormalizationError("Cannot derive a learning outline from empty extracted content.")
        # Adapters budget their own text so they can describe the truncation in
        # their own terms; this is the enforcement that no prompt can exceed it.
        budgeted = apply_text_budget(text, budget_chars=self._budget_chars)
        outline = self._structured_llm.invoke(
            [
                ("system", OUTLINE_SYSTEM_PROMPT),
                (
                    "human",
                    f"Source URL: {source_url}\nMedia type: {media_type}\n\nExtracted content:\n{budgeted.text}",
                ),
            ]
        )
        if not isinstance(outline, LearningOutline):
            raise InputNormalizationError("Outline extraction did not return a structured learning outline.")
        if budgeted.warning:
            return outline.model_copy(update={"warnings": [*outline.warnings, budgeted.warning]})
        return outline


class UrlPageAdapter:
    """Fetch and normalize a validated course or educational page URL."""

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
        self._method = f"url_page_adapter:{settings.url_page_adapter_version}"
        self._outline_method = f"structured_outline:{settings.learning_outline_prompt_version}"

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Return structured learning context derived from one validated URL."""

        if not request.course_url:
            raise InputNormalizationError("URL-page input requires course_url.")

        try:
            extracted = self._extractor.extract_url(request.course_url)
        except Exception as error:  # noqa: BLE001 - provider boundary becomes a domain error
            raise InputNormalizationError(f"Could not extract learning content from URL: {error}") from error
        if not extracted.text.strip():
            raise InputNormalizationError("URL contained no extractable learning content.")

        budgeted = apply_text_budget(extracted.text, budget_chars=self._budget_chars)
        try:
            outline = self._outline_deriver.derive(
                text=budgeted.text,
                source_url=extracted.final_url,
                media_type=extracted.media_type,
            )
        except Exception as error:  # noqa: BLE001 - model/provider boundary becomes a domain error
            raise InputNormalizationError(f"Could not derive a structured learning outline: {error}") from error

        input_kind = _classify_page(extracted, request)
        title = request.course_name or outline.title or extracted.title
        institution = request.university_name or outline.institution
        subject = request.subject or outline.subject
        chapters = _prepend_optional(request.chapter, outline.chapters)
        sections = _merge_values(_split_values(request.sections), outline.sections)
        constraints = _constraints_from(request)
        canonical_url = normalize_url(extracted.final_url)

        provenance = {
            NormalizedLearningField.CANONICAL_IDENTIFIER: self._url_provenance(canonical_url),
            NormalizedLearningField.TOPICS: self._outline_provenance(canonical_url, outline.confidence),
        }
        derived_values = {
            NormalizedLearningField.TITLE: title,
            NormalizedLearningField.INSTITUTION: institution,
            NormalizedLearningField.SUBJECT: subject,
            NormalizedLearningField.CHAPTERS: chapters,
            NormalizedLearningField.SECTIONS: sections,
        }
        for field, value in derived_values.items():
            if value:
                provenance[field] = self._field_provenance(field, request, canonical_url, outline.confidence)
        if constraints != LearningConstraints():
            provenance[NormalizedLearningField.USER_CONSTRAINTS] = FieldProvenance(
                origin=ProvenanceOrigin.USER_INPUT,
                source_reference=InputSourceReference.RESOURCE_PREFERENCES,
                method=self._method,
                confidence=1.0,
            )

        warnings = list(outline.warnings)
        if budgeted.warning:
            warnings.append(budgeted.warning)
        if extracted.media_type == "pdf":
            warnings.append("The submitted URL resolved to a PDF; its text was normalized as an educational page.")

        return NormalizedLearningRequest(
            input_kind=input_kind,
            canonical_identifier=f"url:{canonical_url}",
            title=title,
            institution=institution,
            subject=subject,
            topics=_merge_values(outline.topics, []),
            chapters=chapters,
            sections=sections,
            user_constraints=constraints,
            field_provenance=provenance,
            warnings=warnings,
            confidence=outline.confidence,
        )

    def _url_provenance(self, canonical_url: str) -> FieldProvenance:
        return FieldProvenance(
            origin=ProvenanceOrigin.ADAPTER_DERIVED,
            source_reference=canonical_url,
            method=self._method,
            confidence=1.0,
        )

    def _outline_provenance(self, canonical_url: str, confidence: float) -> FieldProvenance:
        return FieldProvenance(
            origin=ProvenanceOrigin.EXTRACTED_CONTENT,
            source_reference=canonical_url,
            method=self._outline_method,
            confidence=confidence,
        )

    def _field_provenance(
        self,
        field: NormalizedLearningField,
        request: CourseInputRequest,
        canonical_url: str,
        confidence: float,
    ) -> FieldProvenance:
        user_references = {
            NormalizedLearningField.TITLE: (request.course_name, InputSourceReference.COURSE_NAME),
            NormalizedLearningField.INSTITUTION: (request.university_name, InputSourceReference.UNIVERSITY_NAME),
            NormalizedLearningField.SUBJECT: (request.subject, InputSourceReference.SUBJECT),
            NormalizedLearningField.CHAPTERS: (request.chapter, InputSourceReference.CHAPTER),
            NormalizedLearningField.SECTIONS: (request.sections, InputSourceReference.SECTIONS),
        }
        value, reference = user_references[field]
        if value:
            return FieldProvenance(
                origin=ProvenanceOrigin.USER_INPUT,
                source_reference=reference,
                method=self._method,
                confidence=1.0,
            )
        return self._outline_provenance(canonical_url, confidence)


def _classify_page(extracted: ExtractedContent, request: CourseInputRequest) -> LearningInputKind:
    supplied_course_context = any((request.course_name, request.university_name))
    searchable_text = f"{extracted.title or ''}\n{extracted.text[:10000]}".casefold()
    if supplied_course_context or any(marker in searchable_text for marker in COURSE_PAGE_MARKERS):
        return LearningInputKind.COURSE_PAGE
    return LearningInputKind.EDUCATIONAL_PAGE


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
