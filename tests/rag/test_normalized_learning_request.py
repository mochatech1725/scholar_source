"""Tests for the shared normalized learning-request contract."""

import pytest
from pydantic import ValidationError

from backend.rag.models import (
    FieldProvenance,
    LearningConstraints,
    LearningInputKind,
    NormalizedLearningField,
    NormalizedLearningRequest,
    ProvenanceOrigin,
)


def _provenance(
    origin: ProvenanceOrigin = ProvenanceOrigin.USER_INPUT,
) -> FieldProvenance:
    return FieldProvenance(
        origin=origin,
        source_reference="topics_list",
        method="topic_list_adapter:v1",
        confidence=1.0,
    )


def test_normalized_learning_request_preserves_shared_adapter_contract() -> None:
    request = NormalizedLearningRequest(
        input_kind=LearningInputKind.TOPIC_LIST,
        canonical_identifier="topics:vector-calculus",
        title="Vector Calculus Review",
        institution="Example University",
        subject="Mathematics",
        topics=["gradient", "divergence", "curl"],
        chapters=["Chapter 16"],
        sections=["16.1", "16.4"],
        user_constraints=LearningConstraints(
            desired_resource_types=["practice exams"],
            excluded_sites=["example.com"],
        ),
        field_provenance={
            NormalizedLearningField.CANONICAL_IDENTIFIER: _provenance(),
            NormalizedLearningField.TITLE: _provenance(),
            NormalizedLearningField.INSTITUTION: _provenance(),
            NormalizedLearningField.SUBJECT: _provenance(),
            NormalizedLearningField.TOPICS: _provenance(),
            NormalizedLearningField.CHAPTERS: _provenance(),
            NormalizedLearningField.SECTIONS: _provenance(),
            NormalizedLearningField.USER_CONSTRAINTS: _provenance(),
        },
        warnings=[],
        confidence=1.0,
    )

    assert request.input_kind is LearningInputKind.TOPIC_LIST
    assert request.topics == ["gradient", "divergence", "curl"]
    assert request.field_provenance[NormalizedLearningField.TOPICS].origin is ProvenanceOrigin.USER_INPUT


def test_normalized_learning_request_supports_derived_field_provenance() -> None:
    request = NormalizedLearningRequest(
        input_kind=LearningInputKind.COURSE_PAGE,
        canonical_identifier="https://example.edu/calculus",
        subject="Mathematics",
        topics=["gradient"],
        field_provenance={
            NormalizedLearningField.CANONICAL_IDENTIFIER: _provenance(),
            NormalizedLearningField.SUBJECT: _provenance(ProvenanceOrigin.EXTRACTED_CONTENT),
            NormalizedLearningField.TOPICS: _provenance(ProvenanceOrigin.ADAPTER_DERIVED),
        },
        warnings=["Course title was unavailable."],
        confidence=0.8,
    )

    assert request.field_provenance[NormalizedLearningField.TOPICS].confidence == 1.0
    assert request.warnings == ["Course title was unavailable."]


def test_normalized_learning_request_rejects_untraceable_populated_fields() -> None:
    with pytest.raises(ValidationError, match="Missing provenance for normalized fields: subject"):
        NormalizedLearningRequest(
            input_kind=LearningInputKind.ISBN,
            canonical_identifier="9780262046305",
            subject="Computer Science",
            topics=["algorithms"],
            field_provenance={
                NormalizedLearningField.CANONICAL_IDENTIFIER: _provenance(ProvenanceOrigin.PROVIDER_METADATA),
                NormalizedLearningField.TOPICS: _provenance(ProvenanceOrigin.PROVIDER_METADATA),
            },
            confidence=0.9,
        )


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_normalized_learning_request_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        NormalizedLearningRequest(
            input_kind=LearningInputKind.BOOK_METADATA,
            canonical_identifier="book:introduction-to-algorithms",
            topics=["algorithms"],
            field_provenance={
                NormalizedLearningField.CANONICAL_IDENTIFIER: _provenance(),
                NormalizedLearningField.TOPICS: _provenance(),
            },
            confidence=confidence,
        )
