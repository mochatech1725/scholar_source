"""Tests for evidence-only study-guide synthesis."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.rag.config import RagSettings
from backend.rag.errors import SynthesisError
from backend.rag.models import (
    RecommendationDraft,
    SelectedEvidence,
    StudyGuideDraft,
    WeakEvidenceStatus,
)
from backend.rag.synthesis.prompt import SYSTEM_PROMPT, format_evidence_context
from backend.rag.synthesis.synthesizer import (
    INSUFFICIENT_MESSAGE,
    WEAK_PREFIX,
    EvidenceSynthesizer,
)


def _evidence(
    chunk_id: str,
    *,
    title: str,
    content: str,
    evidence_rank: int,
) -> SelectedEvidence:
    return SelectedEvidence(
        chunk_id=UUID(chunk_id),
        source_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        url="https://example.edu/stored-resource",
        title=title,
        chunk_index=evidence_rank - 1,
        content=content,
        semantic_score=0.8,
        rerank_score=0.03,
        evidence_rank=evidence_rank,
    )


def _synthesizer_with(
    draft: StudyGuideDraft,
) -> tuple[EvidenceSynthesizer, MagicMock]:
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = draft
    synthesizer = EvidenceSynthesizer(RagSettings(), llm=mock_llm)
    return synthesizer, mock_llm


def test_synthesizer_generates_a_structured_study_guide() -> None:
    evidence = [
        _evidence(
            "00000000-0000-4000-8000-000000000001",
            title="Vector Calculus Notes",
            content="The gradient points in the direction of steepest increase.",
            evidence_rank=1,
        )
    ]
    expected = StudyGuideDraft(
        overview="Use the notes to review gradients.",
        recommendations=[
            RecommendationDraft(
                resource_title="Vector Calculus Notes",
                why_useful="It explains the geometric meaning of a gradient.",
                how_to_use="Read the explanation, then reproduce the example.",
                supporting_chunk_ids=[str(evidence[0].chunk_id)],
            )
        ],
    )
    synthesizer, _mock_llm = _synthesizer_with(expected)

    guide = synthesizer.synthesize(
        "gradient vectors",
        evidence,
        status=WeakEvidenceStatus.STRONG,
        status_reason=None,
    )

    assert guide == expected


def test_model_receives_only_the_selected_evidence() -> None:
    selected = [
        _evidence(
            "00000000-0000-4000-8000-000000000001",
            title="Selected Notes",
            content="SELECTED_EVIDENCE_MARKER",
            evidence_rank=1,
        )
    ]
    unselected = _evidence(
        "00000000-0000-4000-8000-000000000002",
        title="Unselected Notes",
        content="UNSELECTED_EVIDENCE_MARKER",
        evidence_rank=2,
    )
    synthesizer, mock_llm = _synthesizer_with(StudyGuideDraft(overview="Selected evidence guide."))

    synthesizer.synthesize(
        "gradients",
        selected,
        status=WeakEvidenceStatus.STRONG,
        status_reason=None,
    )

    messages = mock_llm.with_structured_output.return_value.invoke.call_args.args[0]
    assert messages[0] == ("system", SYSTEM_PROMPT)
    assert "SELECTED_EVIDENCE_MARKER" in messages[1][1]
    assert str(selected[0].chunk_id) in messages[1][1]
    assert "UNSELECTED_EVIDENCE_MARKER" not in messages[1][1]
    assert str(unselected.chunk_id) not in messages[1][1]
    assert selected[0].url not in messages[1][1]


def test_context_preserves_selected_evidence_order() -> None:
    evidence = [
        _evidence(
            "00000000-0000-4000-8000-000000000001",
            title="First",
            content="First selected chunk.",
            evidence_rank=1,
        ),
        _evidence(
            "00000000-0000-4000-8000-000000000002",
            title="Second",
            content="Second selected chunk.",
            evidence_rank=2,
        ),
    ]

    context = format_evidence_context(evidence)

    assert context.index(str(evidence[0].chunk_id)) < context.index(str(evidence[1].chunk_id))


def test_recommendation_requires_at_least_one_source_citation() -> None:
    with pytest.raises(ValidationError):
        RecommendationDraft(
            resource_title="Uncited Notes",
            why_useful="It claims to explain gradients.",
            how_to_use="Read it.",
            supporting_chunk_ids=[],
        )


def test_synthesizer_rejects_citations_outside_selected_evidence() -> None:
    evidence = [
        _evidence(
            "00000000-0000-4000-8000-000000000001",
            title="Selected Notes",
            content="Selected evidence about gradients.",
            evidence_rank=1,
        )
    ]
    draft = StudyGuideDraft(
        overview="A guide with an unsupported citation.",
        recommendations=[
            RecommendationDraft(
                resource_title="Unsupported Notes",
                why_useful="It claims to explain gradients.",
                how_to_use="Read it.",
                supporting_chunk_ids=["00000000-0000-4000-8000-000000000099"],
            )
        ],
    )
    synthesizer, _mock_llm = _synthesizer_with(draft)

    with pytest.raises(
        SynthesisError,
        match="not present in selected evidence",
    ):
        synthesizer.synthesize(
            "gradients",
            evidence,
            status=WeakEvidenceStatus.STRONG,
            status_reason=None,
        )


@pytest.mark.parametrize(
    ("evidence", "status"),
    [
        ([], WeakEvidenceStatus.INSUFFICIENT),
        (
            [
                _evidence(
                    "00000000-0000-4000-8000-000000000001",
                    title="Below-threshold Notes",
                    content="Content that did not pass the evidence assessment.",
                    evidence_rank=1,
                )
            ],
            WeakEvidenceStatus.INSUFFICIENT,
        ),
    ],
)
def test_insufficient_evidence_returns_limitation_without_calling_llm(
    evidence: list[SelectedEvidence],
    status: WeakEvidenceStatus,
) -> None:
    synthesizer, mock_llm = _synthesizer_with(StudyGuideDraft(overview="This must not be returned."))

    guide = synthesizer.synthesize(
        "gradients",
        evidence,
        status=status,
        status_reason="No evidence passed retrieval thresholds.",
    )

    mock_llm.with_structured_output.return_value.invoke.assert_not_called()
    assert guide.overview == INSUFFICIENT_MESSAGE
    assert guide.recommendations == []
    assert guide.limitations == "No evidence passed retrieval thresholds."


def test_empty_evidence_is_insufficient_even_when_status_is_strong() -> None:
    synthesizer, mock_llm = _synthesizer_with(StudyGuideDraft(overview="This must not be returned."))

    guide = synthesizer.synthesize(
        "gradients",
        [],
        status=WeakEvidenceStatus.STRONG,
        status_reason=None,
    )

    mock_llm.with_structured_output.return_value.invoke.assert_not_called()
    assert guide.overview == INSUFFICIENT_MESSAGE
    assert guide.limitations == "No usable evidence was retrieved."


def test_weak_evidence_softens_the_generated_guide() -> None:
    evidence = [
        _evidence(
            "00000000-0000-4000-8000-000000000001",
            title="Limited Notes",
            content="One useful but incomplete explanation of gradients.",
            evidence_rank=1,
        )
    ]
    draft = StudyGuideDraft(
        overview="Use these notes to begin reviewing gradients.",
        limitations="The notes do not include worked examples.",
    )
    synthesizer, mock_llm = _synthesizer_with(draft)

    guide = synthesizer.synthesize(
        "gradients",
        evidence,
        status=WeakEvidenceStatus.WEAK,
        status_reason="Only 1 chunk met the strong semantic score threshold.",
    )

    mock_llm.with_structured_output.return_value.invoke.assert_called_once()
    assert guide.overview == f"{WEAK_PREFIX}\n\n{draft.overview}"
    assert guide.limitations == (
        "Only 1 chunk met the strong semantic score threshold.\n\nThe notes do not include worked examples."
    )


def test_unevaluated_evidence_is_rejected_without_calling_llm() -> None:
    evidence = [
        _evidence(
            "00000000-0000-4000-8000-000000000001",
            title="Unevaluated Notes",
            content="Evidence that has not passed the evidence assessment.",
            evidence_rank=1,
        )
    ]
    synthesizer, mock_llm = _synthesizer_with(StudyGuideDraft(overview="This must not be returned."))

    with pytest.raises(SynthesisError, match="must be assessed"):
        synthesizer.synthesize(
            "gradients",
            evidence,
            status=WeakEvidenceStatus.NOT_EVALUATED,
            status_reason=None,
        )

    mock_llm.with_structured_output.return_value.invoke.assert_not_called()
