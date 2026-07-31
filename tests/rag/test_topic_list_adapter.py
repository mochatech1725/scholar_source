"""Tests for deterministic direct topic-list normalization."""

import pytest

from backend.models import CourseInputRequest
from backend.rag.config import DEFAULT_SETTINGS, RagSettings
from backend.rag.errors import InputNormalizationError
from backend.rag.input_adapters import AdapterDispatcher, InputSourceReference, TopicListAdapter
from backend.rag.models import LearningInputKind, NormalizedLearningField, ProvenanceOrigin


def test_topic_list_adapter_preserves_learning_context_and_preferences() -> None:
    request = CourseInputRequest(
        topics_list=" Limits, derivatives, limits,  integrals ",
        course_name="Calculus I",
        university_name="Example University",
        subject="Mathematics",
        chapter="Chapter 2",
        sections="2.1, 2.2, 2.1",
        desired_resource_types=["practice_problem_sets", "lecture_videos"],
        excluded_sites="chegg.com, coursehero.com",
        targeted_sites="mit.edu, stanford.edu",
        preferred_creators="Professor Leonard, 3Blue1Brown",
    )

    result = TopicListAdapter(settings=DEFAULT_SETTINGS).normalize(request)

    assert result.input_kind is LearningInputKind.TOPIC_LIST
    assert result.canonical_identifier.startswith("topics:")
    assert result.title == "Calculus I"
    assert result.institution == "Example University"
    assert result.subject == "Mathematics"
    assert result.topics == ["Limits", "derivatives", "integrals"]
    assert result.chapters == ["Chapter 2"]
    assert result.sections == ["2.1", "2.2"]
    assert result.user_constraints.desired_resource_types == ["practice_problem_sets", "lecture_videos"]
    assert result.user_constraints.excluded_sites == ["chegg.com", "coursehero.com"]
    assert result.user_constraints.targeted_sites == ["mit.edu", "stanford.edu"]
    assert result.user_constraints.preferred_creators == ["Professor Leonard", "3Blue1Brown"]
    assert set(result.field_provenance) == set(NormalizedLearningField) - {NormalizedLearningField.AUTHOR}
    assert all(item.origin is ProvenanceOrigin.USER_INPUT for item in result.field_provenance.values())
    assert result.field_provenance[NormalizedLearningField.TITLE].source_reference == InputSourceReference.COURSE_NAME
    assert (
        result.field_provenance[NormalizedLearningField.USER_CONSTRAINTS].source_reference
        == InputSourceReference.RESOURCE_PREFERENCES
    )
    assert result.warnings == []
    assert result.confidence == 1.0


def test_topic_list_adapter_emits_stable_identifier_for_equivalent_case_and_spacing() -> None:
    adapter = TopicListAdapter(settings=DEFAULT_SETTINGS)

    first = adapter.normalize(CourseInputRequest(topics_list="Limits, derivatives"))
    second = adapter.normalize(CourseInputRequest(topics_list=" limits , DERIVATIVES "))

    assert first.canonical_identifier == second.canonical_identifier


def test_topic_list_adapter_omits_provenance_for_absent_optional_context() -> None:
    result = TopicListAdapter(settings=DEFAULT_SETTINGS).normalize(CourseInputRequest(topics_list="limits"))

    assert set(result.field_provenance) == {
        NormalizedLearningField.CANONICAL_IDENTIFIER,
        NormalizedLearningField.TOPICS,
    }


def test_topic_list_adapter_rejects_delimiters_without_topics() -> None:
    with pytest.raises(InputNormalizationError, match="at least one non-empty topic"):
        TopicListAdapter(settings=DEFAULT_SETTINGS).normalize(CourseInputRequest(topics_list=", ,"))


def test_dispatcher_runs_registered_topic_list_adapter() -> None:
    dispatcher = AdapterDispatcher({LearningInputKind.TOPIC_LIST: TopicListAdapter(settings=DEFAULT_SETTINGS)})

    result = dispatcher.dispatch(CourseInputRequest(topics_list="limits, derivatives"))

    assert result.input_kind is LearningInputKind.TOPIC_LIST
    assert result.topics == ["limits", "derivatives"]


def test_topic_list_adapter_records_configured_version_in_provenance() -> None:
    settings = RagSettings(topic_list_adapter_version="test-version")

    result = TopicListAdapter(settings=settings).normalize(CourseInputRequest(topics_list="limits"))

    assert result.field_provenance[NormalizedLearningField.TOPICS].method == "topic_list_adapter:test-version"
