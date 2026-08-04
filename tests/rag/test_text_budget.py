"""Tests for the extracted-text budget applied before any outline LLM call."""

from __future__ import annotations

import pytest

from backend.rag.input_adapters.text_budget import LINE_BOUNDARY_LOOKBACK_CHARS, apply_text_budget


def test_text_within_budget_is_returned_unchanged() -> None:
    budgeted = apply_text_budget("Limits and derivatives.", budget_chars=100)

    assert budgeted.text == "Limits and derivatives."
    assert budgeted.is_truncated is False
    assert budgeted.warning is None


def test_oversized_text_is_cut_to_the_budget_and_warns() -> None:
    budgeted = apply_text_budget("x" * 500, budget_chars=100)

    assert len(budgeted.text) == 100
    assert budgeted.original_chars == 500
    assert budgeted.is_truncated is True
    assert budgeted.warning == (
        "Only the first 100 of 500 extracted characters were used to derive the learning outline; it may be incomplete."
    )


def test_truncation_prefers_a_nearby_line_boundary() -> None:
    text = "First line.\n" + "x" * 500

    budgeted = apply_text_budget(text, budget_chars=100)

    assert budgeted.text == "First line."


def test_truncation_ignores_a_line_boundary_that_is_too_far_back() -> None:
    text = "First line.\n" + "x" * 5_000
    budget = LINE_BOUNDARY_LOOKBACK_CHARS + 200

    budgeted = apply_text_budget(text, budget_chars=budget)

    assert len(budgeted.text) == budget


def test_truncation_never_returns_empty_text_for_a_leading_newline() -> None:
    budgeted = apply_text_budget("\n" + "x" * 500, budget_chars=100)

    assert budgeted.text.strip() == "x" * 99


def test_budget_must_be_positive() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        apply_text_budget("Limits", budget_chars=0)
