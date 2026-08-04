"""Tests for deterministic normalization of explicit book metadata."""

from backend.models import CourseInputRequest
from backend.rag.config import DEFAULT_SETTINGS, RagSettings
from backend.rag.input_adapters import AdapterDispatcher, BookMetadataAdapter
from backend.rag.models import LearningInputKind, NormalizedLearningField, ProvenanceOrigin


def test_book_metadata_adapter_preserves_all_supported_context() -> None:
    adapter = BookMetadataAdapter(settings=DEFAULT_SETTINGS)

    result = adapter.normalize(
        CourseInputRequest(
            book_title="Introduction to Algorithms",
            book_author="Thomas H. Cormen",
            book_edition="Fourth Edition",
            subject="Computer Science",
            chapter="Chapter 2: Getting Started",
            sections="Insertion sort, Analyzing algorithms, insertion SORT",
            desired_resource_types=["practice_exams_tests"],
        )
    )

    assert result.input_kind is LearningInputKind.BOOK_METADATA
    assert result.title == "Introduction to Algorithms"
    assert result.author == "Thomas H. Cormen"
    assert result.edition == "Fourth Edition"
    assert result.subject == "Computer Science"
    assert result.topics == [
        "Computer Science",
        "Chapter 2: Getting Started",
        "Insertion sort",
        "Analyzing algorithms",
        "Introduction to Algorithms",
    ]
    assert result.chapters == ["Chapter 2: Getting Started"]
    assert result.sections == ["Insertion sort", "Analyzing algorithms"]
    assert result.user_constraints.desired_resource_types == ["practice_exams_tests"]
    assert result.field_provenance[NormalizedLearningField.EDITION].origin is ProvenanceOrigin.USER_INPUT


def test_book_metadata_adapter_supports_legacy_textbook_title_and_dispatch() -> None:
    adapter = BookMetadataAdapter(settings=RagSettings(book_metadata_adapter_version="metadata-test"))
    dispatcher = AdapterDispatcher({LearningInputKind.BOOK_METADATA: adapter})

    result = dispatcher.dispatch(CourseInputRequest(textbook="Structure and Interpretation of Computer Programs"))

    assert result.title == "Structure and Interpretation of Computer Programs"
    assert result.topics == ["Structure and Interpretation of Computer Programs"]
    assert result.field_provenance[NormalizedLearningField.TITLE].source_reference == "textbook"
    assert result.field_provenance[NormalizedLearningField.CANONICAL_IDENTIFIER].method == (
        "book_metadata_adapter:metadata-test"
    )


def test_book_metadata_identifier_is_stable_across_equivalent_casing() -> None:
    adapter = BookMetadataAdapter(settings=DEFAULT_SETTINGS)

    first = adapter.normalize(
        CourseInputRequest(book_title="Clean Code", book_author="Robert Martin", book_edition="1st")
    )
    second = adapter.normalize(
        CourseInputRequest(book_title="clean code", book_author="ROBERT MARTIN", book_edition="1ST")
    )

    assert first.canonical_identifier == second.canonical_identifier


def test_book_metadata_topics_fall_back_to_title_when_context_is_absent() -> None:
    result = BookMetadataAdapter(settings=DEFAULT_SETTINGS).normalize(
        CourseInputRequest(book_title="Linear Algebra Done Right")
    )

    assert result.topics == ["Linear Algebra Done Right"]
    assert result.confidence == 1.0
