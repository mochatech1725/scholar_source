"""Corpus tenancy policy: which sources may enter the shared retrieval corpus.

Plan step 0.6.8. `rag_chunks` and `rag_embeddings` carry no owner column, and
`match_rag_chunks` filters only on embedding model, so every stored chunk is
retrievable by every run. That is safe only while the corpus holds nothing
user-specific, which is the rule enforced here: only sources ScholarSource
discovered on its own — web search results and seed catalog entries — may be
chunked and embedded.

User-supplied URLs are still fetched, but only by the input adapters, which
read a page to derive topics and then discard the text. That text never
becomes a chunk, so it can never surface in another user's retrieval results.
"""

from __future__ import annotations

from backend.rag.errors import CorpusPolicyError
from backend.rag.models import SourceRecord

CORPUS_ELIGIBLE_SOURCE_TYPES: frozenset[str] = frozenset({"web_search", "seed_catalog"})


def is_corpus_eligible(source_type: str) -> bool:
    """Return whether sources of this type may be stored in the shared corpus."""
    return source_type in CORPUS_ELIGIBLE_SOURCE_TYPES


def assert_corpus_eligible(source: SourceRecord) -> None:
    """Raise unless the source was discovered by the pipeline itself.

    Fails closed: an unrecognized source type is rejected rather than trusted,
    so a new input path cannot reach the corpus without an explicit decision
    to add its type here.
    """
    if not is_corpus_eligible(source.source_type):
        allowed = ", ".join(sorted(CORPUS_ELIGIBLE_SOURCE_TYPES))
        raise CorpusPolicyError(
            f"Source type {source.source_type!r} may not enter the shared corpus; "
            f"only pipeline-discovered sources ({allowed}) may be chunked."
        )
