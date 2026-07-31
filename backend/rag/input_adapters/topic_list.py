"""Normalize validated topic-list requests without provider or model calls."""

from __future__ import annotations

from collections.abc import Iterable

from backend.models import CourseInputRequest
from backend.rag.config import RagSettings
from backend.rag.errors import InputNormalizationError
from backend.rag.hashing import sha256_json
from backend.rag.input_adapters.references import InputSourceReference
from backend.rag.models import (
    FieldProvenance,
    LearningConstraints,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
)


class TopicListAdapter:
    """Preserve explicit topic and course context in the shared v2 contract."""

    def __init__(self, *, settings: RagSettings) -> None:
        self._method = f"topic_list_adapter:{settings.topic_list_adapter_version}"

    def normalize(self, request: CourseInputRequest) -> NormalizedLearningRequest:
        """Return a deterministic normalized request from user-authored fields."""

        topics = _split_values(request.topics_list)
        if not topics:
            raise InputNormalizationError("Topic-list input must contain at least one non-empty topic.")

        chapters = [request.chapter] if request.chapter else []
        sections = _split_values(request.sections)
        constraints = LearningConstraints(
            desired_resource_types=list(request.desired_resource_types or []),
            excluded_sites=_split_values(request.excluded_sites),
            targeted_sites=_split_values(request.targeted_sites),
            preferred_creators=_split_values(request.preferred_creators),
        )
        canonical_identifier = f"topics:{sha256_json([topic.casefold() for topic in topics])}"

        provenance = {
            NormalizedLearningField.CANONICAL_IDENTIFIER: self._user_provenance(InputSourceReference.TOPICS_LIST),
            NormalizedLearningField.TOPICS: self._user_provenance(InputSourceReference.TOPICS_LIST),
        }
        optional_provenance = {
            NormalizedLearningField.TITLE: (request.course_name, InputSourceReference.COURSE_NAME),
            NormalizedLearningField.INSTITUTION: (request.university_name, InputSourceReference.UNIVERSITY_NAME),
            NormalizedLearningField.SUBJECT: (request.subject, InputSourceReference.SUBJECT),
            NormalizedLearningField.CHAPTERS: (chapters, InputSourceReference.CHAPTER),
            NormalizedLearningField.SECTIONS: (sections, InputSourceReference.SECTIONS),
        }
        provenance.update(
            {
                field: self._user_provenance(source_reference)
                for field, (value, source_reference) in optional_provenance.items()
                if value
            }
        )
        if constraints != LearningConstraints():
            provenance[NormalizedLearningField.USER_CONSTRAINTS] = self._user_provenance(
                InputSourceReference.RESOURCE_PREFERENCES
            )

        return NormalizedLearningRequest(
            input_kind=LearningInputKind.TOPIC_LIST,
            canonical_identifier=canonical_identifier,
            title=request.course_name,
            institution=request.university_name,
            subject=request.subject,
            topics=topics,
            chapters=chapters,
            sections=sections,
            user_constraints=constraints,
            field_provenance=provenance,
            confidence=1.0,
        )

    def _user_provenance(self, source_reference: InputSourceReference) -> FieldProvenance:
        """Build exact provenance using the configured adapter version."""

        return FieldProvenance(
            origin=ProvenanceOrigin.USER_INPUT,
            source_reference=source_reference.value,
            method=self._method,
            confidence=1.0,
        )


def _split_values(value: str | None) -> list[str]:
    """Split comma-delimited input, preserving order while removing duplicates."""

    if not value:
        return []
    return _unique_values(part.strip() for part in value.split(","))


def _unique_values(values: Iterable[str]) -> list[str]:
    """Return non-empty values once using case-insensitive comparison."""

    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if value and key not in seen:
            unique.append(value)
            seen.add(key)
    return unique
