"""Score semantic and lexical retrieval hits with reciprocal rank fusion."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from backend.rag.config import RagSettings
from backend.rag.models import RetrievalHit, SelectedEvidence, WeakEvidenceStatus


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
    usable_scores: list[tuple[UUID, float]] = []
    for chunk_id, rerank_score in ordered_scores:
        hit = hits_by_id[chunk_id]
        if _is_usable_hit(hit, settings=settings):
            usable_scores.append((chunk_id, rerank_score))

    return [
        _to_selected_evidence(
            hits_by_id[chunk_id],
            rerank_score=rerank_score,
            evidence_rank=evidence_rank,
        )
        for evidence_rank, (chunk_id, rerank_score) in enumerate(
            usable_scores[: settings.evidence_limit],
            start=1,
        )
    ]


def assess_evidence(
    evidence: list[SelectedEvidence],
    *,
    settings: RagSettings,
) -> tuple[WeakEvidenceStatus, str | None]:
    """Classify whether selected evidence can support a confident answer."""
    if not evidence:
        return (
            WeakEvidenceStatus.INSUFFICIENT,
            "No evidence passed retrieval thresholds.",
        )

    strong_count = sum(
        item.semantic_score is not None and item.semantic_score >= settings.weak_semantic_score for item in evidence
    )
    if strong_count >= settings.min_strong_evidence:
        return WeakEvidenceStatus.STRONG, None

    chunk_label = "chunk" if strong_count == 1 else "chunks"
    return (
        WeakEvidenceStatus.WEAK,
        (
            f"Only {strong_count} {chunk_label} met the strong semantic score "
            f"threshold of {settings.weak_semantic_score}; "
            f"{settings.min_strong_evidence} required for a confident answer."
        ),
    )


def _is_usable_hit(hit: RetrievalHit, *, settings: RagSettings) -> bool:
    """Keep lexical hits and semantic hits that meet the configured floor.

    RRF scores encode rank agreement, not absolute relevance, so the semantic
    retrieval score is the appropriate calibrated cutoff. Lexical hits remain
    eligible because their score scale is query-dependent and is not directly
    comparable with cosine similarity.
    """
    if hit.lexical_score is not None:
        return True
    return hit.semantic_score is not None and hit.semantic_score >= settings.min_semantic_score


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
