"""Configuration for the ScholarSource v2 RAG pipeline.

All tunable values live here so Phase 3 evals can sweep them and so every
threshold has one authoritative definition.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RagSettings:
    """Runtime knobs for the deterministic RAG pipeline."""

    # Embeddings: matches the vector(1536) column in rag_embeddings.
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 64

    # Synthesis: temperature 0 + fixed seed per Phase 2 determinism goals.
    chat_model: str = "gpt-4o-mini"
    llm_seed: int = 7
    prompt_version: str = "study-guide-synthesis-v1"

    # Chunking: ~1400 chars is roughly 350 tokens. Large enough that a chunk
    # carries a complete explanation, small enough that retrieval stays
    # precise. Overlap keeps definitions that straddle a boundary retrievable
    # from both neighboring chunks.
    chunk_target_chars: int = 1400
    chunk_overlap_chars: int = 200
    chunk_min_chars: int = 200

    # Retrieval and reranking.
    retrieval_limit: int = 12
    lexical_limit: int = 12
    rrf_k: int = 60
    evidence_limit: int = 6

    # Weak-evidence policy (starting points; tune with Phase 3 evals).
    # Below min_semantic_score a hit is treated as noise. Between the two
    # thresholds evidence is usable but the answer must be softened.
    min_semantic_score: float = 0.25
    weak_semantic_score: float = 0.35
    min_strong_evidence: int = 3

    # Source collection and extraction.
    max_sources_per_run: int = 8
    results_per_query: int = 5
    fetch_timeout_seconds: float = 15.0
    max_fetch_bytes: int = 2_000_000


DEFAULT_SETTINGS = RagSettings()
