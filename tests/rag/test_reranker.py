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
    semantic_score: float | None = None,
    lexical_score: float | None = None,
) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=UUID(chunk_id),
        source_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        url="https://example.edu/vector-calculus",
        title="Vector Calculus Notes",
        chunk_index=0,
        content="The gradient points in the direction of steepest increase.",
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


def test_scoring_respects_the_configured_evidence_limit() -> None:
    settings = replace(SETTINGS, evidence_limit=1)
    semantic_hits = [
        _hit("00000000-0000-4000-8000-000000000001", semantic_score=0.9),
        _hit("00000000-0000-4000-8000-000000000002", semantic_score=0.8),
    ]

    evidence = rerank_evidence(semantic_hits, [], settings=settings)

    assert len(evidence) == settings.evidence_limit
    assert evidence[0].chunk_id == semantic_hits[0].chunk_id
