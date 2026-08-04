"""Normalize user-supplied book metadata without provider or model calls."""

from __future__ import annotations

from backend.models import CourseInputRequest
from backend.rag.config import RagSettings
from backend.rag.errors import InputNormalizationError
from backend.rag.hashing import sha256_json
from backend.rag.input_adapters.book_url import _constraints_from, _merge_values, _split_values
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.models import (
    FieldProvenance,
    LearningConstraints,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
)


class BookMetadataAdapter:
    """Turn explicit bibliographic and learning fields into one request."""

    def __init__(self, *, settings: RagSettings) -> None:
        self._method = f"book_metadata_adapter:{settings.book_metadata_adapter_version}"

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Normalize title metadata and preserve all explicit learning context."""

        title = request.book_title or request.textbook
        if not title:
            raise InputNormalizationError("Book-metadata input requires book_title or textbook.")

        chapters = [request.chapter] if request.chapter else []
        sections = _split_values(request.sections)
        topics = _merge_values(
            [request.subject] if request.subject else [],
            [*chapters, *sections, title],
        )
        constraints = _constraints_from(request)
        identifier_values = {
            "title": title.casefold(),
            "author": request.book_author.casefold() if request.book_author else None,
            "edition": request.book_edition.casefold() if request.book_edition else None,
        }
        title_reference = InputSourceReference.BOOK_TITLE if request.book_title else InputSourceReference.TEXTBOOK
        provenance = {
            NormalizedLearningField.CANONICAL_IDENTIFIER: self._provenance(title_reference),
            NormalizedLearningField.TITLE: self._provenance(title_reference),
            NormalizedLearningField.TOPICS: self._provenance(self._topic_reference(request)),
        }
        optional_fields = {
            NormalizedLearningField.AUTHOR: (request.book_author, InputSourceReference.BOOK_AUTHOR),
            NormalizedLearningField.EDITION: (request.book_edition, InputSourceReference.BOOK_EDITION),
            NormalizedLearningField.SUBJECT: (request.subject, InputSourceReference.SUBJECT),
            NormalizedLearningField.CHAPTERS: (chapters, InputSourceReference.CHAPTER),
            NormalizedLearningField.SECTIONS: (sections, InputSourceReference.SECTIONS),
        }
        provenance.update(
            {field: self._provenance(reference) for field, (value, reference) in optional_fields.items() if value}
        )
        if constraints != LearningConstraints():
            provenance[NormalizedLearningField.USER_CONSTRAINTS] = self._provenance(
                InputSourceReference.RESOURCE_PREFERENCES
            )

        return NormalizedLearningRequest(
            input_kind=LearningInputKind.BOOK_METADATA,
            canonical_identifier=f"book:{sha256_json(identifier_values)}",
            title=title,
            author=request.book_author,
            edition=request.book_edition,
            subject=request.subject,
            topics=topics,
            chapters=chapters,
            sections=sections,
            user_constraints=constraints,
            field_provenance=provenance,
            confidence=1.0,
        )

    def _provenance(self, reference: InputSourceReference) -> FieldProvenance:
        return FieldProvenance(
            origin=ProvenanceOrigin.USER_INPUT,
            source_reference=reference,
            method=self._method,
            confidence=1.0,
        )

    @staticmethod
    def _topic_reference(request: CourseInputRequest) -> InputSourceReference:
        if request.subject:
            return InputSourceReference.SUBJECT
        if request.chapter:
            return InputSourceReference.CHAPTER
        if request.sections:
            return InputSourceReference.SECTIONS
        if request.book_title:
            return InputSourceReference.BOOK_TITLE
        return InputSourceReference.TEXTBOOK
