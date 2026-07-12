"""Supabase/pgvector persistence for RAG source and chunk records."""

from __future__ import annotations

from uuid import UUID

from backend.database import get_supabase_client
from backend.rag.errors import VectorStoreError
from backend.rag.models import (
    ChunkRecord,
    EmbeddingRecord,
    ExtractedDocument,
    RetrievalHit,
    SourceRecord,
)
from backend.rag.sources.policy import DomainPolicy, DomainRule
from supabase import Client


class SupabaseVectorStore:
    """Persist source, extraction, chunk, and embedding rows."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase_client(use_service_role=True)

    def upsert_source(self, source: SourceRecord) -> UUID:
        """Insert or refresh a source row keyed by normalized URL."""
        response = (
            self._client.table("rag_sources")
            .upsert(
                {
                    "url": source.url,
                    "normalized_url": source.normalized_url,
                    "title": source.title,
                    "source_type": source.source_type,
                    "quality_status": source.quality_status.value,
                    "quality_reason": source.quality_reason,
                    "metadata": source.metadata,
                },
                on_conflict="normalized_url",
            )
            .execute()
        )
        if not response.data:
            raise VectorStoreError(f"Failed to upsert source {source.normalized_url}.")
        return UUID(response.data[0]["id"])

    def record_rejection(self, run_id: UUID, source: SourceRecord) -> None:
        """Persist a rejected candidate source for run traceability."""
        self._client.table("rag_source_rejections").insert(
            {
                "run_id": str(run_id),
                "url": source.url,
                "normalized_url": source.normalized_url,
                "rejection_reason": source.quality_reason,
                "metadata": source.metadata,
            }
        ).execute()

    def fetch_domain_policy(self) -> DomainPolicy:
        """Load source-quality domain rules from storage."""
        response = (
            self._client.table("rag_domain_policies")
            .select("pattern, match_type, policy, reason")
            .order("pattern")
            .execute()
        )
        if not response.data:
            raise VectorStoreError("rag_domain_policies is empty; apply migration 003 seed rows.")

        return DomainPolicy(
            rules=tuple(
                DomainRule(
                    pattern=row["pattern"],
                    match_type=row["match_type"],
                    policy=row["policy"],
                    reason=row.get("reason"),
                )
                for row in response.data
            )
        )

    def find_extracted_document(self, source_id: UUID, text_hash: str) -> UUID | None:
        """Return the cached extracted document id for unchanged source text."""
        response = (
            self._client.table("rag_extracted_documents")
            .select("id")
            .eq("source_id", str(source_id))
            .eq("extracted_text_hash", text_hash)
            .limit(1)
            .execute()
        )
        return UUID(response.data[0]["id"]) if response.data else None

    def insert_extracted_document(self, document: ExtractedDocument) -> UUID:
        """Upsert extracted document metadata and return its id."""
        response = (
            self._client.table("rag_extracted_documents")
            .upsert(
                {
                    "source_id": str(document.source_id),
                    "url": document.url,
                    "title": document.title,
                    "extracted_text_hash": document.extracted_text_hash,
                    "extraction_status": document.extraction_status.value,
                    "extraction_error": document.extraction_error,
                    "metadata": document.metadata,
                },
                on_conflict="source_id,extracted_text_hash",
            )
            .execute()
        )
        if not response.data:
            raise VectorStoreError(f"Failed to insert extracted document for {document.url}.")
        return UUID(response.data[0]["id"])

    def upsert_chunks(self, chunks: list[ChunkRecord]) -> list[UUID]:
        """Upsert chunk rows and return their ids in input order."""
        if not chunks:
            return []

        response = (
            self._client.table("rag_chunks")
            .upsert(
                [
                    {
                        "source_id": str(chunk.source_id),
                        "extracted_document_id": str(chunk.extracted_document_id)
                        if chunk.extracted_document_id
                        else None,
                        "url": chunk.url,
                        "title": chunk.title,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "content_hash": chunk.content_hash,
                        "embedding_model": chunk.embedding_model,
                        "token_count": chunk.token_count,
                        "metadata": chunk.metadata,
                    }
                    for chunk in chunks
                ],
                on_conflict="source_id,chunk_index,content_hash",
            )
            .execute()
        )
        if len(response.data) != len(chunks):
            raise VectorStoreError("Chunk upsert returned an unexpected row count.")
        return [UUID(row["id"]) for row in response.data]

    def existing_embedding_hashes(self, content_hashes: list[str], embedding_model: str) -> set[str]:
        """Return content hashes already embedded with the given model."""
        if not content_hashes:
            return set()

        response = (
            self._client.table("rag_embeddings")
            .select("content_hash")
            .eq("embedding_model", embedding_model)
            .in_("content_hash", content_hashes)
            .execute()
        )
        return {row["content_hash"] for row in response.data}

    def insert_embeddings(self, embeddings: list[EmbeddingRecord]) -> int:
        """Insert embedding rows while preserving repeated-run idempotency."""
        if not embeddings:
            return 0

        response = (
            self._client.table("rag_embeddings")
            .upsert(
                [
                    {
                        "chunk_id": str(record.chunk_id),
                        "content_hash": record.content_hash,
                        "embedding_model": record.embedding_model,
                        "embedding_dimensions": record.embedding_dimensions,
                        "embedding": record.embedding,
                    }
                    for record in embeddings
                ],
                on_conflict="chunk_id,embedding_model",
                ignore_duplicates=True,
            )
            .execute()
        )
        return len(response.data)

    def semantic_search(self, query_embedding: list[float], *, limit: int, embedding_model: str) -> list[RetrievalHit]:
        """Search chunks by cosine similarity through the pgvector RPC."""
        response = self._client.rpc(
            "match_rag_chunks",
            {
                "query_embedding": query_embedding,
                "match_limit": limit,
                "model_filter": embedding_model,
            },
        ).execute()
        return [_hit_from_row(row, semantic_score=float(row["similarity"])) for row in response.data]

    def lexical_search(self, query_text: str, *, limit: int) -> list[RetrievalHit]:
        """Search chunks by Postgres full-text ranking through the lexical RPC."""
        response = self._client.rpc(
            "search_rag_chunks_lexical",
            {"query_text": query_text, "match_limit": limit},
        ).execute()
        return [_hit_from_row(row, lexical_score=float(row["lexical_score"])) for row in response.data]

    def chunks_for_source(self, source_id: UUID) -> list[dict]:
        """Return stored chunks for one source in source order."""
        response = (
            self._client.table("rag_chunks")
            .select("id, chunk_index, content, content_hash")
            .eq("source_id", str(source_id))
            .order("chunk_index")
            .execute()
        )
        return response.data

    def delete_source(self, normalized_url: str) -> None:
        """Delete one local test source and its cascading RAG rows."""
        self._client.table("rag_sources").delete().eq("normalized_url", normalized_url).execute()


def _hit_from_row(
    row: dict,
    *,
    semantic_score: float | None = None,
    lexical_score: float | None = None,
) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=UUID(row["chunk_id"]),
        source_id=UUID(row["source_id"]),
        url=row["url"],
        title=row["title"],
        chunk_index=row["chunk_index"],
        content=row["content"],
        content_hash=row["content_hash"],
        semantic_score=semantic_score,
        lexical_score=lexical_score,
    )
