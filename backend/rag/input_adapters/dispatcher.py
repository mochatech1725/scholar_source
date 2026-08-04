"""Select exactly one normalization adapter from validated request fields."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from backend.models import CourseInputRequest
from backend.rag.errors import AmbiguousLearningInputError, UnsupportedLearningInputError
from backend.rag.models import LearningInputKind, NormalizedLearningRequest


class InputAdapter(Protocol):
    """Contract implemented by each input-specific normalizer."""

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Normalize one validated API request into the shared v2 contract."""


@dataclass(frozen=True, slots=True)
class PrimaryInputSelection:
    """Deterministic route selected from one complete primary input group."""

    input_kind: LearningInputKind
    populated_fields: tuple[str, ...]


def select_primary_input(request: CourseInputRequest) -> PrimaryInputSelection:
    """Return the sole primary input route or reject an invalid combination."""

    selections = _primary_input_selections(request)
    if len(selections) > 1:
        fields = ", ".join(field for selection in selections for field in selection.populated_fields)
        raise AmbiguousLearningInputError(
            f"Conflicting primary learning inputs were provided: {fields}. Submit exactly one primary input."
        )
    if selections:
        return selections[0]

    if request.book_author:
        raise UnsupportedLearningInputError("Book author requires book_title or textbook.")
    raise UnsupportedLearningInputError(
        "No supported primary learning input was provided. Submit topics_list, course_url, book_url, "
        "ISBN, or book title metadata."
    )


class AdapterDispatcher:
    """Route a validated request to its registered input adapter."""

    def __init__(self, adapters: Mapping[LearningInputKind, InputAdapter]) -> None:
        self._adapters = dict(adapters)

    def dispatch(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Normalize a request through the one adapter selected by its fields."""

        selection = select_primary_input(request)
        adapter = self._adapters.get(selection.input_kind)
        if adapter is None:
            raise UnsupportedLearningInputError(f"No input adapter is registered for {selection.input_kind.value}.")
        return adapter.normalize(request)


def _primary_input_selections(request: CourseInputRequest) -> list[PrimaryInputSelection]:
    selections: list[PrimaryInputSelection] = []
    scalar_inputs = (
        ("topics_list", LearningInputKind.TOPIC_LIST),
        ("course_url", LearningInputKind.COURSE_PAGE),
        ("book_url", LearningInputKind.BOOK_URL),
        ("isbn", LearningInputKind.ISBN),
    )
    for field_name, input_kind in scalar_inputs:
        if getattr(request, field_name):
            selections.append(PrimaryInputSelection(input_kind=input_kind, populated_fields=(field_name,)))

    metadata_fields = tuple(field_name for field_name in ("book_title", "textbook") if getattr(request, field_name))
    book_context_kinds = {
        LearningInputKind.BOOK_URL,
        LearningInputKind.ISBN,
    }
    has_book_primary_input = any(selection.input_kind in book_context_kinds for selection in selections)
    if metadata_fields and not has_book_primary_input:
        selections.append(
            PrimaryInputSelection(
                input_kind=LearningInputKind.BOOK_METADATA,
                populated_fields=metadata_fields,
            )
        )
    return selections
