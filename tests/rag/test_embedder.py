from uuid import uuid4

import pytest

from backend.rag.config import RagSettings
from backend.rag.embeddings import ChunkEmbedder
from backend.rag.errors import EmbeddingError
from backend.rag.hashing import sha256_text
from backend.rag.models import ChunkRecord


class FakeEmbeddings:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.texts = texts
        return self.vectors


def _chunk(content: str, *, persisted: bool = True) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=uuid4() if persisted else None,
        source_id=uuid4(),
        extracted_document_id=uuid4(),
        url="https://ocw.mit.edu/course-notes",
        title="Course Notes",
        chunk_index=0,
        content=content,
        content_hash=sha256_text(content),
        embedding_model="text-embedding-3-small",
    )


def test_embed_chunks_generates_embedding_records_for_persisted_chunks() -> None:
    settings = RagSettings(
        embedding_model="text-embedding-3-small-test-version",
        embedding_dimensions=3,
        embedding_batch_size=2,
    )
    chunks = [_chunk("first chunk about vectors"), _chunk("second chunk about matrices")]
    provider = FakeEmbeddings([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

    records = ChunkEmbedder(settings=settings, embeddings=provider).embed_chunks(chunks)

    assert provider.texts == [chunk.content for chunk in chunks]
    assert [record.chunk_id for record in records] == [chunk.chunk_id for chunk in chunks]
    assert [record.content_hash for record in records] == [chunk.content_hash for chunk in chunks]
    assert all(record.embedding_model == settings.embedding_model for record in records)
    assert all(record.embedding_dimensions == settings.embedding_dimensions for record in records)
    assert [record.embedding for record in records] == provider.vectors


def test_embed_chunks_logs_embedding_model_used(caplog: pytest.LogCaptureFixture) -> None:
    settings = RagSettings(
        embedding_model="text-embedding-3-small-test-version",
        embedding_dimensions=3,
    )
    provider = FakeEmbeddings([[0.1, 0.2, 0.3]])

    with caplog.at_level("INFO", logger="backend.rag.embeddings.embedder"):
        ChunkEmbedder(settings=settings, embeddings=provider).embed_chunks([_chunk("logged chunk")])

    record = next(item for item in caplog.records if item.message == "Generating embeddings")
    assert record.embedding_model == settings.embedding_model
    assert record.embedding_dimensions == settings.embedding_dimensions
    assert record.chunk_count == 1


def test_embed_chunks_requires_persisted_chunks_for_traceability() -> None:
    provider = FakeEmbeddings([[0.1, 0.2, 0.3]])
    embedder = ChunkEmbedder(settings=RagSettings(embedding_dimensions=3), embeddings=provider)

    with pytest.raises(EmbeddingError, match="persisted before embedding"):
        embedder.embed_chunks([_chunk("unpersisted chunk", persisted=False)])


def test_embed_chunks_rejects_provider_count_mismatch() -> None:
    chunks = [_chunk("first"), _chunk("second")]
    provider = FakeEmbeddings([[0.1, 0.2, 0.3]])
    embedder = ChunkEmbedder(settings=RagSettings(embedding_dimensions=3), embeddings=provider)

    with pytest.raises(EmbeddingError, match="Embedding count 1 does not match chunk count 2"):
        embedder.embed_chunks(chunks)


def test_embed_chunks_rejects_wrong_vector_dimensions() -> None:
    provider = FakeEmbeddings([[0.1, 0.2]])
    embedder = ChunkEmbedder(settings=RagSettings(embedding_dimensions=3), embeddings=provider)

    with pytest.raises(EmbeddingError, match="Expected 3-dim vectors"):
        embedder.embed_chunks([_chunk("short vector")])


def test_embed_chunks_returns_empty_list_for_empty_input() -> None:
    provider = FakeEmbeddings([])
    embedder = ChunkEmbedder(settings=RagSettings(embedding_dimensions=3), embeddings=provider)

    assert embedder.embed_chunks([]) == []
    assert provider.texts == []
