from __future__ import annotations

from math import sqrt
from typing import Any
from uuid import UUID, uuid4

import pytest

from backend.rag.config import RagSettings
from backend.rag.embeddings import RagEmbedder
from backend.rag.hashing import sha256_text
from backend.rag.models import (
    ChunkRecord,
    EmbeddingRecord,
    ExtractedDocument,
    ExtractionStatus,
    QualityStatus,
    SourceRecord,
)
from backend.rag.vector_store import SupabaseVectorStore


class FakeResponse:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    def execute(self) -> FakeResponse:
        return self


class KnownQueryEmbeddings:
    def __init__(self, query_vectors: dict[str, list[float]]) -> None:
        self._query_vectors = query_vectors
        self.queries: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise AssertionError(f"Unexpected document embedding request: {texts}")

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return self._query_vectors[text]


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "rag_sources": [],
            "rag_source_rejections": [],
            "rag_extracted_documents": [],
            "rag_chunks": [],
            "rag_embeddings": [],
            "rag_domain_policies": [],
        }

    def table(self, table_name: str) -> FakeTableQuery:
        return FakeTableQuery(self, table_name)

    def rpc(self, function_name: str, params: dict[str, Any]) -> FakeResponse:
        if function_name == "search_rag_chunks_lexical":
            query_terms = params["query_text"].lower().split()
            rows = [
                {
                    "chunk_id": chunk["id"],
                    "source_id": chunk["source_id"],
                    "url": chunk["url"],
                    "title": chunk["title"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "content_hash": chunk["content_hash"],
                    "lexical_score": sum(term in chunk["content"].lower() for term in query_terms),
                }
                for chunk in self.tables["rag_chunks"]
                if any(term in chunk["content"].lower() for term in query_terms)
            ]
            rows.sort(key=lambda row: row["lexical_score"], reverse=True)
            return FakeResponse(rows[: params["match_limit"]])

        if function_name != "match_rag_chunks":
            raise AssertionError(f"Unexpected RPC: {function_name}")

        rows = []
        model_filter = params["model_filter"]
        query_embedding = params["query_embedding"]
        for embedding in self.tables["rag_embeddings"]:
            if embedding["embedding_model"] != model_filter:
                continue
            chunk = self._row_by_id("rag_chunks", embedding["chunk_id"])
            rows.append(
                {
                    "chunk_id": chunk["id"],
                    "source_id": chunk["source_id"],
                    "url": chunk["url"],
                    "title": chunk["title"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "content_hash": chunk["content_hash"],
                    "embedding_model": embedding["embedding_model"],
                    "similarity": _cosine_similarity(query_embedding, embedding["embedding"]),
                }
            )

        rows.sort(key=lambda row: row["similarity"], reverse=True)
        return FakeResponse(rows[: params["match_limit"]])

    def _row_by_id(self, table_name: str, row_id: str) -> dict[str, Any]:
        return next(row for row in self.tables[table_name] if row["id"] == row_id)

    def delete_source(self, normalized_url: str) -> None:
        source_ids = {row["id"] for row in self.tables["rag_sources"] if row["normalized_url"] == normalized_url}
        chunk_ids = {row["id"] for row in self.tables["rag_chunks"] if row["source_id"] in source_ids}
        self.tables["rag_sources"] = [row for row in self.tables["rag_sources"] if row["id"] not in source_ids]
        self.tables["rag_extracted_documents"] = [
            row for row in self.tables["rag_extracted_documents"] if row["source_id"] not in source_ids
        ]
        self.tables["rag_chunks"] = [row for row in self.tables["rag_chunks"] if row["source_id"] not in source_ids]
        self.tables["rag_embeddings"] = [
            row for row in self.tables["rag_embeddings"] if row["chunk_id"] not in chunk_ids
        ]


class FakeTableQuery:
    def __init__(self, client: FakeSupabaseClient, table_name: str) -> None:
        self.client = client
        self.table_name = table_name
        self.filters: list[tuple[str, Any]] = []
        self.in_filters: list[tuple[str, set[Any]]] = []
        self.order_column: str | None = None
        self.limit_count: int | None = None
        self.pending_rows: list[dict[str, Any]] | None = None
        self.mode: str = "select"

    def upsert(
        self,
        values: dict[str, Any] | list[dict[str, Any]],
        *,
        on_conflict: str,
        ignore_duplicates: bool = False,
    ) -> FakeTableQuery:
        del ignore_duplicates
        self.mode = "upsert"
        self.pending_rows = values if isinstance(values, list) else [values]
        self.conflict_columns = on_conflict.split(",")
        return self

    def insert(self, values: dict[str, Any]) -> FakeResponse:
        row = {**values, "id": str(uuid4())}
        self.client.tables[self.table_name].append(row)
        return FakeResponse([row])

    def select(self, _columns: str = "*") -> FakeTableQuery:
        self.mode = "select"
        return self

    def delete(self) -> FakeTableQuery:
        self.mode = "delete"
        return self

    def eq(self, column: str, value: Any) -> FakeTableQuery:
        self.filters.append((column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> FakeTableQuery:
        self.in_filters.append((column, set(values)))
        return self

    def order(self, column: str) -> FakeTableQuery:
        self.order_column = column
        return self

    def limit(self, count: int) -> FakeTableQuery:
        self.limit_count = count
        return self

    def execute(self) -> FakeResponse:
        if self.mode == "upsert":
            return FakeResponse(self._upsert_rows())
        if self.mode == "delete":
            if self.table_name == "rag_sources":
                normalized_url = next(value for column, value in self.filters if column == "normalized_url")
                self.client.delete_source(normalized_url)
            return FakeResponse([])

        rows = [row for row in self.client.tables[self.table_name] if self._matches(row)]
        if self.order_column is not None:
            rows.sort(key=lambda row: row[self.order_column])
        if self.limit_count is not None:
            rows = rows[: self.limit_count]
        return FakeResponse(rows)

    def _upsert_rows(self) -> list[dict[str, Any]]:
        assert self.pending_rows is not None

        stored_rows = self.client.tables[self.table_name]
        result = []
        for pending in self.pending_rows:
            existing = next(
                (row for row in stored_rows if all(row[column] == pending[column] for column in self.conflict_columns)),
                None,
            )
            if existing is None:
                existing = {**pending, "id": str(uuid4())}
                stored_rows.append(existing)
            else:
                existing.update(pending)
            result.append(existing)
        return result

    def _matches(self, row: dict[str, Any]) -> bool:
        return all(row[column] == value for column, value in self.filters) and all(
            row[column] in values for column, values in self.in_filters
        )


def _source() -> SourceRecord:
    return SourceRecord(
        url="https://ocw.mit.edu/courses/vector-calculus",
        normalized_url="https://ocw.mit.edu/courses/vector-calculus",
        title="Vector Calculus",
        source_type="course_notes",
        quality_status=QualityStatus.ACCEPTED,
        quality_reason="open courseware source",
    )


def _document(source_id: UUID) -> ExtractedDocument:
    text = "Gradient, divergence, and curl study notes."
    return ExtractedDocument(
        source_id=source_id,
        url="https://ocw.mit.edu/courses/vector-calculus",
        title="Vector Calculus",
        text=text,
        extracted_text_hash=sha256_text(text),
        extraction_status=ExtractionStatus.COMPLETED,
    )


def _chunk(source_id: UUID, document_id: UUID, index: int, content: str) -> ChunkRecord:
    return ChunkRecord(
        source_id=source_id,
        extracted_document_id=document_id,
        url="https://ocw.mit.edu/courses/vector-calculus",
        title="Vector Calculus",
        chunk_index=index,
        content=content,
        content_hash=sha256_text(content),
        embedding_model="text-embedding-3-small",
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def test_inserted_chunks_can_be_retrieved_by_source_and_semantic_similarity() -> None:
    client = FakeSupabaseClient()
    store = SupabaseVectorStore(client=client)
    source_id = store.upsert_source(_source())
    document_id = store.insert_extracted_document(_document(source_id))
    chunks = [
        _chunk(source_id, document_id, 1, "Curl measures local rotation in a vector field."),
        _chunk(source_id, document_id, 0, "Gradient points in the direction of steepest increase."),
        _chunk(source_id, document_id, 2, "Divergence measures net outward flux."),
    ]

    chunk_ids = store.upsert_chunks(chunks)
    store.insert_embeddings(
        [
            EmbeddingRecord(
                chunk_id=chunk_id,
                content_hash=chunk.content_hash,
                embedding_model=chunk.embedding_model,
                embedding_dimensions=3,
                embedding=vector,
            )
            for chunk_id, chunk, vector in zip(
                chunk_ids,
                chunks,
                [[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.2, 0.8]],
                strict=True,
            )
        ]
    )

    source_chunks = store.chunks_for_source(source_id)
    semantic_hits = store.semantic_search([1.0, 0.0, 0.0], limit=2, embedding_model="text-embedding-3-small")

    assert [row["chunk_index"] for row in source_chunks] == [0, 1, 2]
    assert [row["content"] for row in source_chunks] == [
        "Gradient points in the direction of steepest increase.",
        "Curl measures local rotation in a vector field.",
        "Divergence measures net outward flux.",
    ]
    assert semantic_hits[0].chunk_id == chunk_ids[1]
    assert semantic_hits[0].content == chunks[1].content
    assert [hit.chunk_id for hit in semantic_hits] == [chunk_ids[1], chunk_ids[0]]
    assert [hit.semantic_score for hit in semantic_hits] == pytest.approx([1.0, 0.0])
    assert all(hit.lexical_score is None for hit in semantic_hits)
    assert len(semantic_hits) == 2


@pytest.mark.parametrize(
    ("query", "expected_chunk_index"),
    [
        ("Which direction does the gradient point?", 0),
        ("What does curl measure in a vector field?", 1),
        ("How is divergence related to outward flux?", 2),
    ],
)
def test_known_queries_retrieve_expected_source_chunks(query: str, expected_chunk_index: int) -> None:
    client = FakeSupabaseClient()
    store = SupabaseVectorStore(client=client)
    source_id = store.upsert_source(_source())
    document_id = store.insert_extracted_document(_document(source_id))
    chunks = [
        _chunk(source_id, document_id, 0, "Gradient points in the direction of steepest increase."),
        _chunk(source_id, document_id, 1, "Curl measures local rotation in a vector field."),
        _chunk(source_id, document_id, 2, "Divergence measures net outward flux."),
    ]
    chunk_vectors = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    chunk_ids = store.upsert_chunks(chunks)
    store.insert_embeddings(
        [
            EmbeddingRecord(
                chunk_id=chunk_id,
                content_hash=chunk.content_hash,
                embedding_model=chunk.embedding_model,
                embedding_dimensions=3,
                embedding=vector,
            )
            for chunk_id, chunk, vector in zip(chunk_ids, chunks, chunk_vectors, strict=True)
        ]
    )
    query_vectors = {
        "Which direction does the gradient point?": [0.9, 0.1, 0.0],
        "What does curl measure in a vector field?": [0.1, 0.9, 0.0],
        "How is divergence related to outward flux?": [0.0, 0.1, 0.9],
    }
    provider = KnownQueryEmbeddings(query_vectors)
    embedder = RagEmbedder(
        settings=RagSettings(embedding_dimensions=3),
        embeddings=provider,
    )

    query_embedding = embedder.embed_query(query)
    hits = store.semantic_search(
        query_embedding,
        limit=1,
        embedding_model="text-embedding-3-small",
    )

    assert provider.queries == [query]
    assert len(hits) == 1
    assert hits[0].chunk_id == chunk_ids[expected_chunk_index]
    assert hits[0].source_id == source_id
    assert hits[0].chunk_index == expected_chunk_index
    assert hits[0].content == chunks[expected_chunk_index].content
    assert hits[0].semantic_score is not None
    assert hits[0].semantic_score > 0.99


def test_search_hits_preserve_stored_chunk_citation_metadata() -> None:
    client = FakeSupabaseClient()
    store = SupabaseVectorStore(client=client)
    source_id = store.upsert_source(_source())
    document_id = store.insert_extracted_document(_document(source_id))
    chunk = _chunk(source_id, document_id, 0, "Gradient points toward steepest increase.")
    chunk_id = store.upsert_chunks([chunk])[0]
    store.insert_embeddings(
        [
            EmbeddingRecord(
                chunk_id=chunk_id,
                content_hash=chunk.content_hash,
                embedding_model=chunk.embedding_model,
                embedding_dimensions=3,
                embedding=[1.0, 0.0, 0.0],
            )
        ]
    )

    semantic_hit = store.semantic_search(
        [1.0, 0.0, 0.0],
        limit=1,
        embedding_model="text-embedding-3-small",
    )[0]
    lexical_hit = store.lexical_search("gradient", limit=1)[0]

    for hit in (semantic_hit, lexical_hit):
        assert hit.chunk_id == chunk_id
        assert hit.source_id == source_id
        assert hit.url == chunk.url
        assert hit.title == chunk.title
        assert hit.chunk_index == chunk.chunk_index
        assert hit.content == chunk.content
        assert hit.content_hash == chunk.content_hash


def test_delete_source_resets_one_local_test_source_and_cascading_rows() -> None:
    client = FakeSupabaseClient()
    store = SupabaseVectorStore(client=client)
    source_id = store.upsert_source(_source())
    document_id = store.insert_extracted_document(_document(source_id))
    chunk_id = store.upsert_chunks([_chunk(source_id, document_id, 0, "Local test chunk.")])[0]
    store.insert_embeddings(
        [
            EmbeddingRecord(
                chunk_id=chunk_id,
                content_hash=sha256_text("Local test chunk."),
                embedding_model="text-embedding-3-small",
                embedding_dimensions=3,
                embedding=[1.0, 0.0, 0.0],
            )
        ]
    )

    store.delete_source("https://ocw.mit.edu/courses/vector-calculus")

    assert client.tables["rag_sources"] == []
    assert client.tables["rag_extracted_documents"] == []
    assert client.tables["rag_chunks"] == []
    assert client.tables["rag_embeddings"] == []
