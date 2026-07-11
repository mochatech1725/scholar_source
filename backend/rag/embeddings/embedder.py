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


class ChunkEmbedder:
    """Create embedding records for persisted chunks."""

    def __init__(
        self,
        *,
        settings: RagSettings,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self._settings = settings
        self._embeddings = embeddings or OpenAIEmbeddings(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            chunk_size=settings.embedding_batch_size,
        )

    def embed_chunks(self, chunks: Sequence[ChunkRecord]) -> list[EmbeddingRecord]:
        """Generate embedding records for chunks in source order."""
        if not chunks:
            return []
        if any(chunk.chunk_id is None for chunk in chunks):
            raise EmbeddingError("Chunks must be persisted before embedding.")

        logger.info(
            "Generating embeddings",
            extra={
                "embedding_model": self._settings.embedding_model,
                "embedding_dimensions": self._settings.embedding_dimensions,
                "chunk_count": len(chunks),
            },
        )
        vectors = self._embeddings.embed_documents([chunk.content for chunk in chunks])
        self._validate(chunks, vectors)

        return [
            EmbeddingRecord(
                chunk_id=chunk.chunk_id,
                content_hash=chunk.content_hash,
                embedding_model=self._settings.embedding_model,
                embedding_dimensions=self._settings.embedding_dimensions,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

    def _validate(self, chunks: Sequence[ChunkRecord], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise EmbeddingError(f"Embedding count {len(vectors)} does not match chunk count {len(chunks)}.")

        bad_sizes = {len(vector) for vector in vectors if len(vector) != self._settings.embedding_dimensions}
        if bad_sizes:
            raise EmbeddingError(
                f"Expected {self._settings.embedding_dimensions}-dim vectors, found {sorted(bad_sizes)}."
            )
