"""Score semantic and lexical retrieval hits with reciprocal rank fusion."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from backend.rag.config import RagSettings
from backend.rag.models import RetrievalHit, SelectedEvidence


def rerank_evidence(
    semantic_hits: list[RetrievalHit],
    lexical_hits: list[RetrievalHit],
    *,
    settings: RagSettings,
) -> list[SelectedEvidence]:
    """Score retrieved chunks against the original need using RRF.

    Both input lists must have been retrieved for the same original user need.
    Reciprocal rank fusion combines their rank positions without comparing the
    incompatible raw semantic and lexical score scales.
    """
    fused_scores: defaultdict[UUID, float] = defaultdict(float)
    hits_by_id: dict[UUID, RetrievalHit] = {}

    for ranked_hits in (semantic_hits, lexical_hits):
        for rank, hit in enumerate(ranked_hits, start=1):
            fused_scores[hit.chunk_id] += 1.0 / (settings.rrf_k + rank)
            hits_by_id[hit.chunk_id] = _merge_hit_scores(hits_by_id.get(hit.chunk_id), hit)

    ordered_scores = sorted(
        fused_scores.items(),
        key=lambda item: (-item[1], str(item[0])),
    )
    return [
        _to_selected_evidence(
            hits_by_id[chunk_id],
            rerank_score=rerank_score,
            evidence_rank=evidence_rank,
        )
        for evidence_rank, (chunk_id, rerank_score) in enumerate(
            ordered_scores[: settings.evidence_limit],
            start=1,
        )
    ]


def _merge_hit_scores(
    existing: RetrievalHit | None,
    incoming: RetrievalHit,
) -> RetrievalHit:
    """Merge retrieval-path scores for the same stored chunk."""
    if existing is None:
        return incoming

    return existing.model_copy(
        update={
            "semantic_score": (
                existing.semantic_score if existing.semantic_score is not None else incoming.semantic_score
            ),
            "lexical_score": (existing.lexical_score if existing.lexical_score is not None else incoming.lexical_score),
        }
    )


def _to_selected_evidence(
    hit: RetrievalHit,
    *,
    rerank_score: float,
    evidence_rank: int,
) -> SelectedEvidence:
    """Copy a scored retrieval hit into the evidence contract."""
    return SelectedEvidence(
        chunk_id=hit.chunk_id,
        source_id=hit.source_id,
        url=hit.url,
        title=hit.title,
        chunk_index=hit.chunk_index,
        content=hit.content,
        semantic_score=hit.semantic_score,
        lexical_score=hit.lexical_score,
        rerank_score=rerank_score,
        evidence_rank=evidence_rank,
    )
