"""Generate embedding vectors for persisted RAG chunks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from langchain_openai import OpenAIEmbeddings

from backend.logging_config import get_logger
from backend.rag.config import RagSettings
from backend.rag.errors import EmbeddingError
from backend.rag.models import ChunkRecord, EmbeddingRecord

logger = get_logger(__name__)


class EmbeddingProvider(Protocol):
    """Minimal provider interface used by the chunk embedder."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""


class ExistingEmbeddingIndex(Protocol):
    """Lookup interface for hashes that already have stored embeddings."""

    def existing_embedding_hashes(self, content_hashes: Sequence[str], embedding_model: str) -> set[str]:
        """Return content hashes already embedded for the given model."""


class ChunkEmbedder:
    """Create embedding records for persisted chunks."""

    def __init__(
        self,
        *,
        settings: RagSettings,
        embeddings: EmbeddingProvider | None = None,
        existing_index: ExistingEmbeddingIndex | None = None,
    ) -> None:
        self._settings = settings
        self._embeddings = embeddings or OpenAIEmbeddings(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            chunk_size=settings.embedding_batch_size,
        )
        self._existing_index = existing_index

    def embed_chunks(self, chunks: Sequence[ChunkRecord]) -> list[EmbeddingRecord]:
        """Generate embedding records for chunks whose content is not embedded yet."""
        if not chunks:
            return []
        if any(chunk.chunk_id is None for chunk in chunks):
            raise EmbeddingError("Chunks must be persisted before embedding.")

        pending_chunks = self._pending_unique_chunks(chunks)
        logger.info(
            "Generating embeddings",
            extra={
                "embedding_model": self._settings.embedding_model,
                "embedding_dimensions": self._settings.embedding_dimensions,
                "chunk_count": len(chunks),
                "pending_chunk_count": len(pending_chunks),
                "skipped_chunk_count": len(chunks) - len(pending_chunks),
            },
        )
        if not pending_chunks:
            return []

        vectors = self._embeddings.embed_documents([chunk.content for chunk in pending_chunks])
        self._validate(pending_chunks, vectors)

        return [
            EmbeddingRecord(
                chunk_id=chunk.chunk_id,
                content_hash=chunk.content_hash,
                embedding_model=self._settings.embedding_model,
                embedding_dimensions=self._settings.embedding_dimensions,
                embedding=vector,
            )
            for chunk, vector in zip(pending_chunks, vectors, strict=True)
        ]

    def _pending_unique_chunks(self, chunks: Sequence[ChunkRecord]) -> list[ChunkRecord]:
        existing_hashes: set[str] = set()
        if self._existing_index is not None:
            existing_hashes = self._existing_index.existing_embedding_hashes(
                [chunk.content_hash for chunk in chunks],
                self._settings.embedding_model,
            )

        pending_chunks: list[ChunkRecord] = []
        seen_hashes = set(existing_hashes)
        for chunk in chunks:
            if chunk.content_hash in seen_hashes:
                continue
            seen_hashes.add(chunk.content_hash)
            pending_chunks.append(chunk)
        return pending_chunks

    def _validate(self, chunks: Sequence[ChunkRecord], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise EmbeddingError(f"Embedding count {len(vectors)} does not match chunk count {len(chunks)}.")

        bad_sizes = {len(vector) for vector in vectors if len(vector) != self._settings.embedding_dimensions}
        if bad_sizes:
            raise EmbeddingError(
                f"Expected {self._settings.embedding_dimensions}-dim vectors, found {sorted(bad_sizes)}."
            )
