"""Tests for deterministic retrieval-hit scoring."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest

from backend.rag.config import RagSettings
from backend.rag.models import RetrievalHit
from backend.rag.reranking.reranker import rerank_evidence

SETTINGS = RagSettings(rrf_k=60, evidence_limit=6)


def _rrf_contribution(rank: int) -> float:
    """Return the expected RRF contribution for one result-list rank."""
    return 1 / (SETTINGS.rrf_k + rank)


def _hit(
    chunk_id: str,
    *,
    content: str = "The gradient points in the direction of steepest increase.",
    semantic_score: float | None = None,
    lexical_score: float | None = None,
) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=UUID(chunk_id),
        source_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        url="https://example.edu/vector-calculus",
        title="Vector Calculus Notes",
        chunk_index=0,
        content=content,
        content_hash=f"hash-{chunk_id}",
        semantic_score=semantic_score,
        lexical_score=lexical_score,
    )


def test_scores_chunks_from_both_original_need_rankings() -> None:
    shared_id = "00000000-0000-4000-8000-000000000001"
    semantic_id = "00000000-0000-4000-8000-000000000002"
    lexical_id = "00000000-0000-4000-8000-000000000003"
    first_rank = 1
    second_rank = 2

    evidence = rerank_evidence(
        [
            _hit(semantic_id, semantic_score=0.91),
            _hit(shared_id, semantic_score=0.84),
        ],
        [
            _hit(shared_id, lexical_score=0.72),
            _hit(lexical_id, lexical_score=0.63),
        ],
        settings=SETTINGS,
    )

    assert [str(item.chunk_id) for item in evidence] == [
        shared_id,
        semantic_id,
        lexical_id,
    ]
    assert evidence[0].rerank_score == pytest.approx(_rrf_contribution(second_rank) + _rrf_contribution(first_rank))
    assert evidence[1].rerank_score == pytest.approx(_rrf_contribution(first_rank))
    assert evidence[2].rerank_score == pytest.approx(_rrf_contribution(second_rank))
    assert [item.evidence_rank for item in evidence] == list(range(1, len(evidence) + 1))


def test_final_relevance_ranking_is_separate_from_retrieval_similarity() -> None:
    semantic_nearest_id = "00000000-0000-4000-8000-000000000001"
    multi_path_id = "00000000-0000-4000-8000-000000000002"

    evidence = rerank_evidence(
        [
            _hit(semantic_nearest_id, semantic_score=0.96),
            _hit(multi_path_id, semantic_score=0.81),
        ],
        [_hit(multi_path_id, lexical_score=0.74)],
        settings=SETTINGS,
    )

    assert [str(item.chunk_id) for item in evidence[:2]] == [
        multi_path_id,
        semantic_nearest_id,
    ]
    assert evidence[0].semantic_score == 0.81
    assert evidence[0].lexical_score == 0.74
    assert evidence[0].evidence_rank == 1
    assert evidence[1].semantic_score == 0.96
    assert evidence[1].lexical_score is None
    assert evidence[1].evidence_rank == 2
    assert evidence[0].rerank_score > evidence[1].rerank_score


def test_reranking_promotes_the_more_useful_multi_path_chunk() -> None:
    semantic_nearest_id = "00000000-0000-4000-8000-000000000001"
    useful_chunk_id = "00000000-0000-4000-8000-000000000002"
    semantic_nearest_content = "A gradient is a vector made from partial derivatives."
    useful_content = "Use the gradient to find the direction of steepest increase in this worked example."

    evidence = rerank_evidence(
        [
            _hit(
                semantic_nearest_id,
                content=semantic_nearest_content,
                semantic_score=0.97,
            ),
            _hit(
                useful_chunk_id,
                content=useful_content,
                semantic_score=0.83,
            ),
        ],
        [
            _hit(
                useful_chunk_id,
                content=useful_content,
                lexical_score=0.76,
            ),
        ],
        settings=SETTINGS,
    )

    assert evidence[0].chunk_id == UUID(useful_chunk_id)
    assert evidence[0].content == useful_content
    assert evidence[0].semantic_score < evidence[1].semantic_score
    assert evidence[0].lexical_score == 0.76
    assert evidence[0].rerank_score > evidence[1].rerank_score
    assert evidence[1].chunk_id == UUID(semantic_nearest_id)
    assert evidence[1].content == semantic_nearest_content


def test_scoring_preserves_zero_raw_scores_and_citation_metadata() -> None:
    chunk_id = "00000000-0000-4000-8000-000000000001"

    evidence = rerank_evidence(
        [_hit(chunk_id, semantic_score=0.0)],
        [_hit(chunk_id, lexical_score=0.0)],
        settings=SETTINGS,
    )

    assert len(evidence) == 1
    assert evidence[0].semantic_score == 0.0
    assert evidence[0].lexical_score == 0.0
    assert evidence[0].url == "https://example.edu/vector-calculus"
    assert evidence[0].title == "Vector Calculus Notes"
    assert evidence[0].source_id == UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def test_selected_evidence_serializes_original_retrieval_scores_for_debugging() -> None:
    chunk_id = "00000000-0000-4000-8000-000000000001"

    evidence = rerank_evidence(
        [_hit(chunk_id, semantic_score=0.87)],
        [_hit(chunk_id, lexical_score=0.42)],
        settings=SETTINGS,
    )

    debug_record = evidence[0].model_dump(mode="json")

    assert debug_record["semantic_score"] == 0.87
    assert debug_record["lexical_score"] == 0.42


def test_selected_evidence_serializes_rerank_score_for_debugging() -> None:
    chunk_id = "00000000-0000-4000-8000-000000000001"

    evidence = rerank_evidence(
        [_hit(chunk_id, semantic_score=0.87)],
        [_hit(chunk_id, lexical_score=0.42)],
        settings=SETTINGS,
    )

    debug_record = evidence[0].model_dump(mode="json")

    assert debug_record["rerank_score"] == pytest.approx(_rrf_contribution(1) + _rrf_contribution(1))
    assert debug_record["evidence_rank"] == 1


def test_scoring_respects_the_configured_evidence_limit() -> None:
    settings = replace(SETTINGS, evidence_limit=1)
    semantic_hits = [
        _hit("00000000-0000-4000-8000-000000000001", semantic_score=0.9),
        _hit("00000000-0000-4000-8000-000000000002", semantic_score=0.8),
    ]

    evidence = rerank_evidence(semantic_hits, [], settings=settings)

    assert len(evidence) == settings.evidence_limit
    assert evidence[0].chunk_id == semantic_hits[0].chunk_id
