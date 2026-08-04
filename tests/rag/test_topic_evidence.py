"""Tests for the derived-topic evidence check."""

import pytest

from backend.rag.config import DEFAULT_SETTINGS
from backend.rag.input_adapters.topic_evidence import filter_supported_topics

PAGE_TEXT = (
    "Course description. This course covers limits, derivatives, and the "
    "fundamental theorem of calculus. Learning objectives include integration "
    "techniques and series convergence."
)


def _filter(topics: list[str], *, evidence_text: str = PAGE_TEXT):
    return filter_supported_topics(
        topics,
        evidence_text=evidence_text,
        min_coverage=DEFAULT_SETTINGS.min_topic_evidence_coverage,
        max_topic_chars=DEFAULT_SETTINGS.max_topic_chars,
    )


def test_topics_drawn_from_the_evidence_are_kept_in_order() -> None:
    result = _filter(["Limits", "Integration techniques", "Series convergence"])

    assert result.topics == ["Limits", "Integration techniques", "Series convergence"]
    assert result.dropped_count == 0
    assert result.warning is None


def test_topics_built_from_absent_vocabulary_are_dropped() -> None:
    result = _filter(["Limits", "Quantum chromodynamics"])

    assert result.topics == ["Limits"]
    assert result.dropped_count == 1


def test_warning_reports_the_count_without_repeating_dropped_text() -> None:
    result = _filter(["Limits", "Discounted pharmaceutical coupon codes"])

    assert result.warning is not None
    assert "1 derived topic(s) were dropped" in result.warning
    assert "coupon" not in result.warning


def test_plurals_match_their_singular_form_in_both_directions() -> None:
    result = _filter(["Derivative", "Limit"], evidence_text="Derivatives and limits are covered.")

    assert result.topics == ["Derivative", "Limit"]


def test_stopwords_do_not_carry_a_topic() -> None:
    result = _filter(["The of and in", "Theorem of calculus"])

    assert result.topics == ["Theorem of calculus"]


@pytest.mark.parametrize(
    "topic",
    [
        "Limits at https://redirect.example/payload",
        "Limits www.redirect.example",
        "Limits course@redirect.example",
    ],
)
def test_address_shaped_topics_are_dropped_even_when_the_page_contains_them(topic: str) -> None:
    evidence = f"Course description covering limits. Contact {topic}."

    result = _filter([topic], evidence_text=evidence)

    assert result.topics == []
    assert result.dropped_count == 1


def test_prose_length_and_multiline_topics_are_dropped() -> None:
    long_topic = "Limits " * 40
    multiline = "Limits\nDerivatives"

    result = _filter([long_topic, multiline, "Limits"])

    assert result.topics == ["Limits"]
    assert result.dropped_count == 2


def test_every_topic_may_be_dropped() -> None:
    result = _filter(["Quantum chromodynamics", "Baroque counterpoint"])

    assert result.topics == []
    assert result.dropped_count == 2
    assert result.warning is not None


@pytest.mark.parametrize(("min_coverage", "max_topic_chars"), [(0.0, 120), (1.5, 120), (0.5, 0)])
def test_invalid_thresholds_are_rejected(min_coverage: float, max_topic_chars: int) -> None:
    with pytest.raises(ValueError):
        filter_supported_topics(
            ["Limits"],
            evidence_text=PAGE_TEXT,
            min_coverage=min_coverage,
            max_topic_chars=max_topic_chars,
        )
