"""Tests for ISBN validation, provider lookup, caching, and normalization."""

from dataclasses import dataclass, field

import pytest

from backend.models import CourseInputRequest
from backend.rag.config import DEFAULT_SETTINGS, RagSettings
from backend.rag.errors import IsbnNormalizationError
from backend.rag.input_adapters import (
    AdapterDispatcher,
    CachedIsbnMetadataProvider,
    IsbnAdapter,
    IsbnMetadata,
    canonicalize_isbn,
)
from backend.rag.models import LearningInputKind, NormalizedLearningField, ProvenanceOrigin


@dataclass
class StubProvider:
    metadata: IsbnMetadata | None = None
    error: Exception | None = None
    calls: list[str] = field(default_factory=list)

    def resolve(self, isbn13: str) -> IsbnMetadata | None:
        self.calls.append(isbn13)
        if self.error:
            raise self.error
        return self.metadata


def _metadata(**overrides: object) -> IsbnMetadata:
    values = {
        "title": "The C Programming Language",
        "authors": ["Brian W. Kernighan", "Dennis M. Ritchie"],
        "subjects": ["C programming", "Computer programming", "c programming"],
        "table_of_contents": ["A Tutorial Introduction", "Types, Operators, and Expressions"],
        "provider_name": "catalog-test",
        "provider_version": "2026-01",
        "record_reference": "catalog-test:9780131103627",
        "confidence": 0.92,
    }
    values.update(overrides)
    return IsbnMetadata.model_validate(values)


@pytest.mark.parametrize(
    ("submitted", "canonical"),
    [
        ("0-13-110362-8", "9780131103627"),
        ("978-0-13-110362-7", "9780131103627"),
        ("0 8044 2957 X", "9780804429573"),
    ],
)
def test_canonicalize_isbn_validates_and_converts_both_formats(submitted: str, canonical: str) -> None:
    assert canonicalize_isbn(submitted) == canonical


@pytest.mark.parametrize("isbn", ["0-13-110362-7", "9780131103628", "123456789A", "123"])
def test_canonicalize_isbn_rejects_invalid_values(isbn: str) -> None:
    with pytest.raises(ValueError):
        canonicalize_isbn(isbn)


def test_isbn_adapter_normalizes_provider_and_user_context_with_provenance() -> None:
    provider = StubProvider(metadata=_metadata())
    adapter = IsbnAdapter(settings=DEFAULT_SETTINGS, provider=provider)

    result = adapter.normalize(
        CourseInputRequest(
            isbn="0-13-110362-8",
            chapter="Pointers and Arrays",
            sections="Pointers, Address Arithmetic",
            desired_resource_types=["lecture_videos"],
        )
    )

    assert provider.calls == ["9780131103627"]
    assert result.input_kind is LearningInputKind.ISBN
    assert result.canonical_identifier == "isbn:9780131103627"
    assert result.title == "The C Programming Language"
    assert result.author == "Brian W. Kernighan, Dennis M. Ritchie"
    assert result.subject == "C programming"
    assert result.topics == ["C programming", "Computer programming"]
    assert result.chapters == [
        "Pointers and Arrays",
        "A Tutorial Introduction",
        "Types, Operators, and Expressions",
    ]
    assert result.sections == ["Pointers", "Address Arithmetic"]
    assert result.field_provenance[NormalizedLearningField.TOPICS].origin is ProvenanceOrigin.PROVIDER_METADATA
    assert result.field_provenance[NormalizedLearningField.TOPICS].method == "catalog-test:2026-01"
    assert result.field_provenance[NormalizedLearningField.CHAPTERS].origin is ProvenanceOrigin.USER_INPUT


def test_isbn_adapter_uses_table_of_contents_when_subjects_are_unavailable() -> None:
    adapter = IsbnAdapter(settings=DEFAULT_SETTINGS, provider=StubProvider(metadata=_metadata(subjects=[])))

    result = adapter.normalize(CourseInputRequest(isbn="9780131103627"))

    assert result.subject is None
    assert result.topics == ["A Tutorial Introduction", "Types, Operators, and Expressions"]


def test_isbn_adapter_preserves_user_author_provenance_when_provider_omits_authors() -> None:
    adapter = IsbnAdapter(settings=DEFAULT_SETTINGS, provider=StubProvider(metadata=_metadata(authors=[])))

    result = adapter.normalize(CourseInputRequest(isbn="9780131103627", book_author="Dennis Ritchie"))

    assert result.author == "Dennis Ritchie"
    assert result.field_provenance[NormalizedLearningField.AUTHOR].origin is ProvenanceOrigin.USER_INPUT


def test_cached_provider_caches_records_and_misses_by_canonical_isbn() -> None:
    provider = StubProvider(metadata=None)
    cached_provider = CachedIsbnMetadataProvider(provider)

    assert cached_provider.resolve("9780131103627") is None
    assert cached_provider.resolve("9780131103627") is None
    assert provider.calls == ["9780131103627"]


@pytest.mark.parametrize(
    ("provider", "code"),
    [
        (StubProvider(metadata=None), "isbn_not_found"),
        (StubProvider(metadata=_metadata(subjects=[], table_of_contents=[])), "insufficient_learning_context"),
        (StubProvider(error=RuntimeError("offline")), "provider_error"),
    ],
)
def test_isbn_adapter_fails_transparently(provider: StubProvider, code: str) -> None:
    adapter = IsbnAdapter(settings=DEFAULT_SETTINGS, provider=provider)

    with pytest.raises(IsbnNormalizationError) as raised:
        adapter.normalize(CourseInputRequest(isbn="9780131103627"))

    assert raised.value.code == code


def test_isbn_adapter_rechecks_checksum_after_request_format_validation() -> None:
    adapter = IsbnAdapter(settings=DEFAULT_SETTINGS, provider=StubProvider(metadata=_metadata()))

    with pytest.raises(IsbnNormalizationError) as raised:
        adapter.normalize(CourseInputRequest(isbn="9780131103628"))

    assert raised.value.code == "invalid_isbn"


def test_isbn_adapter_records_adapter_version_and_dispatches() -> None:
    adapter = IsbnAdapter(
        settings=RagSettings(isbn_adapter_version="isbn-test"),
        provider=StubProvider(metadata=_metadata()),
    )
    dispatcher = AdapterDispatcher({LearningInputKind.ISBN: adapter})

    result = dispatcher.dispatch(CourseInputRequest(isbn="9780131103627"))

    provenance = result.field_provenance[NormalizedLearningField.CANONICAL_IDENTIFIER]
    assert provenance.method == "isbn_adapter:isbn-test"
