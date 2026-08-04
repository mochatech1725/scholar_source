"""Tests for deterministic v2 input-adapter routing."""

from dataclasses import dataclass

import pytest

from backend.models import CourseInputRequest
from backend.rag.errors import AmbiguousLearningInputError, UnsupportedLearningInputError
from backend.rag.input_adapters import AdapterDispatcher, select_primary_input
from backend.rag.models import (
    FieldProvenance,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
)


@pytest.mark.parametrize(
    ("input_request", "expected_kind", "expected_fields"),
    [
        (CourseInputRequest(topics_list="limits, derivatives"), LearningInputKind.TOPIC_LIST, ("topics_list",)),
        (CourseInputRequest(course_url="https://example.edu/course"), LearningInputKind.COURSE_PAGE, ("course_url",)),
        (CourseInputRequest(book_url="https://example.com/book"), LearningInputKind.BOOK_URL, ("book_url",)),
        (CourseInputRequest(isbn="9780262046305"), LearningInputKind.ISBN, ("isbn",)),
        (
            CourseInputRequest(book_title="Algorithms", book_author="Ada Author"),
            LearningInputKind.BOOK_METADATA,
            ("book_title",),
        ),
    ],
)
def test_select_primary_input_routes_validated_fields(
    input_request: CourseInputRequest,
    expected_kind: LearningInputKind,
    expected_fields: tuple[str, ...],
) -> None:
    selection = select_primary_input(input_request)

    assert selection.input_kind is expected_kind
    assert selection.populated_fields == expected_fields


def test_select_primary_input_rejects_conflicting_primary_inputs() -> None:
    request = CourseInputRequest(
        topics_list="limits",
        course_url="https://example.edu/course",
        isbn="9780262046305",
    )

    with pytest.raises(
        AmbiguousLearningInputError,
        match=r"topics_list, course_url, isbn.*exactly one primary input",
    ):
        select_primary_input(request)


@pytest.mark.parametrize(
    ("input_request", "message"),
    [
        (CourseInputRequest(course_name="Calculus I"), "No supported primary"),
        (CourseInputRequest(book_author="Ada Author"), "requires book_title or textbook"),
    ],
)
def test_select_primary_input_rejects_missing_or_incomplete_input(
    input_request: CourseInputRequest,
    message: str,
) -> None:
    with pytest.raises(UnsupportedLearningInputError, match=message):
        select_primary_input(input_request)


@dataclass
class StubAdapter:
    input_kind: LearningInputKind
    received_request: CourseInputRequest | None = None

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        self.received_request = request
        provenance = FieldProvenance(
            origin=ProvenanceOrigin.USER_INPUT,
            source_reference="topics_list",
            method="stub:v1",
            confidence=1.0,
        )
        return NormalizedLearningRequest(
            input_kind=self.input_kind,
            canonical_identifier="topics:limits",
            topics=["limits"],
            field_provenance={
                NormalizedLearningField.CANONICAL_IDENTIFIER: provenance,
                NormalizedLearningField.TOPICS: provenance,
            },
            confidence=1.0,
        )


def test_dispatcher_invokes_only_the_selected_adapter() -> None:
    topic_adapter = StubAdapter(LearningInputKind.TOPIC_LIST)
    isbn_adapter = StubAdapter(LearningInputKind.ISBN)
    dispatcher = AdapterDispatcher(
        {
            LearningInputKind.TOPIC_LIST: topic_adapter,
            LearningInputKind.ISBN: isbn_adapter,
        }
    )
    request = CourseInputRequest(topics_list="limits")

    result = dispatcher.dispatch(request)

    assert result.input_kind is LearningInputKind.TOPIC_LIST
    assert topic_adapter.received_request is request
    assert isbn_adapter.received_request is None


def test_dispatcher_rejects_a_selected_route_without_registered_adapter() -> None:
    dispatcher = AdapterDispatcher({})

    with pytest.raises(UnsupportedLearningInputError, match="course_page"):
        dispatcher.dispatch(CourseInputRequest(course_url="https://example.edu/course"))
