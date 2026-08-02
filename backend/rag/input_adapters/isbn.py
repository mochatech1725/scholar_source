"""Normalize ISBN inputs through a cacheable bibliographic provider boundary."""

from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from typing import Protocol

from pydantic import Field

from backend.models import CourseInputRequest
from backend.rag.config import RagSettings
from backend.rag.errors import IsbnNormalizationError
from backend.rag.input_adapters.book_url import _constraints_from, _merge_values, _split_values
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.models import (
    FieldProvenance,
    LearningConstraints,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
    RagModel,
)


class IsbnMetadata(RagModel):
    """Provider-neutral bibliographic and learning metadata for one edition."""

    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    table_of_contents: list[str] = Field(default_factory=list)
    provider_name: str = Field(min_length=1)
    provider_version: str = Field(min_length=1)
    record_reference: str = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class IsbnMetadataProvider(Protocol):
    """Resolve provider metadata for a canonical ISBN-13."""

    def resolve(self, isbn13: str) -> IsbnMetadata | None:
        """Return provider metadata, or ``None`` when no record exists."""


class CachedIsbnMetadataProvider:
    """Cache provider results, including misses, by canonical ISBN-13."""

    def __init__(
        self,
        provider: IsbnMetadataProvider,
        *,
        cache: MutableMapping[str, IsbnMetadata | None] | None = None,
    ) -> None:
        self._provider = provider
        self._cache = cache if cache is not None else {}

    def resolve(self, isbn13: str) -> IsbnMetadata | None:
        """Return cached metadata before consulting the wrapped provider."""

        if isbn13 not in self._cache:
            self._cache[isbn13] = self._provider.resolve(isbn13)
        return self._cache[isbn13]


class IsbnAdapter:
    """Validate an ISBN and turn provider metadata into learning context."""

    def __init__(self, *, settings: RagSettings, provider: IsbnMetadataProvider) -> None:
        self._provider = provider
        self._method = f"isbn_adapter:{settings.isbn_adapter_version}"

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Resolve one ISBN without hiding invalid, missing, or thin metadata."""

        if not request.isbn:
            raise IsbnNormalizationError("missing_isbn", "ISBN input requires isbn.")
        try:
            isbn13 = canonicalize_isbn(request.isbn)
        except ValueError as error:
            raise IsbnNormalizationError("invalid_isbn", str(error)) from error

        try:
            metadata = self._provider.resolve(isbn13)
        except Exception as error:  # noqa: BLE001 - provider boundary becomes a domain error
            raise IsbnNormalizationError("provider_error", f"Could not resolve ISBN metadata: {error}") from error
        if metadata is None:
            raise IsbnNormalizationError("isbn_not_found", f"No bibliographic record was found for ISBN {isbn13}.")

        subjects = _unique_values(metadata.subjects)
        contents = _unique_values(metadata.table_of_contents)
        if not subjects and not contents:
            raise IsbnNormalizationError(
                "insufficient_learning_context",
                "ISBN metadata did not include subject or table-of-contents learning context.",
            )

        topics = subjects or contents
        chapters = _merge_values([request.chapter] if request.chapter else [], contents)
        sections = _split_values(request.sections)
        provider_author = ", ".join(_unique_values(metadata.authors))
        author = provider_author or request.book_author
        constraints = _constraints_from(request)
        provider_provenance = FieldProvenance(
            origin=ProvenanceOrigin.PROVIDER_METADATA,
            source_reference=metadata.record_reference,
            method=f"{metadata.provider_name}:{metadata.provider_version}",
            confidence=metadata.confidence,
        )
        provenance = {
            NormalizedLearningField.CANONICAL_IDENTIFIER: FieldProvenance(
                origin=ProvenanceOrigin.ADAPTER_DERIVED,
                source_reference=InputSourceReference.ISBN,
                method=self._method,
                confidence=1.0,
            ),
            NormalizedLearningField.TITLE: provider_provenance,
            NormalizedLearningField.TOPICS: provider_provenance,
        }
        if author:
            provenance[NormalizedLearningField.AUTHOR] = (
                provider_provenance
                if provider_author
                else _user_provenance(InputSourceReference.BOOK_AUTHOR, self._method)
            )
        if subjects:
            provenance[NormalizedLearningField.SUBJECT] = provider_provenance
        if chapters:
            provenance[NormalizedLearningField.CHAPTERS] = (
                _user_provenance(InputSourceReference.CHAPTER, self._method) if request.chapter else provider_provenance
            )
        if sections:
            provenance[NormalizedLearningField.SECTIONS] = _user_provenance(InputSourceReference.SECTIONS, self._method)
        if constraints != LearningConstraints():
            provenance[NormalizedLearningField.USER_CONSTRAINTS] = _user_provenance(
                InputSourceReference.RESOURCE_PREFERENCES, self._method
            )

        return NormalizedLearningRequest(
            input_kind=LearningInputKind.ISBN,
            canonical_identifier=f"isbn:{isbn13}",
            title=metadata.title,
            author=author,
            subject=subjects[0] if subjects else None,
            topics=topics,
            chapters=chapters,
            sections=sections,
            user_constraints=constraints,
            field_provenance=provenance,
            warnings=list(metadata.warnings),
            confidence=metadata.confidence,
        )


def canonicalize_isbn(value: str) -> str:
    """Validate an ISBN checksum and return its canonical ISBN-13 digits."""

    compact = "".join(character for character in value.upper() if character not in " -")
    if len(compact) == 10:
        if not compact[:9].isdigit() or (not compact[-1].isdigit() and compact[-1] != "X"):
            raise ValueError("ISBN-10 must contain nine digits followed by a digit or X.")
        checksum = sum(
            (10 - index) * (10 if character == "X" else int(character)) for index, character in enumerate(compact)
        )
        if checksum % 11:
            raise ValueError("ISBN-10 checksum is invalid.")
        base = f"978{compact[:9]}"
        return f"{base}{_isbn13_check_digit(base)}"
    if len(compact) == 13:
        if not compact.isdigit():
            raise ValueError("ISBN-13 must contain only digits.")
        if int(compact[-1]) != _isbn13_check_digit(compact[:12]):
            raise ValueError("ISBN-13 checksum is invalid.")
        return compact
    raise ValueError("ISBN must contain 10 or 13 characters after removing spaces and hyphens.")


def _isbn13_check_digit(first_twelve: str) -> int:
    weighted_sum = sum(int(character) * (1 if index % 2 == 0 else 3) for index, character in enumerate(first_twelve))
    return (10 - weighted_sum % 10) % 10


def _unique_values(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if normalized and normalized.casefold() not in seen:
            result.append(normalized)
            seen.add(normalized.casefold())
    return result


def _user_provenance(source_reference: InputSourceReference, method: str) -> FieldProvenance:
    return FieldProvenance(
        origin=ProvenanceOrigin.USER_INPUT,
        source_reference=source_reference,
        method=method,
        confidence=1.0,
    )
