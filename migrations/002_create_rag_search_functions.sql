-- ScholarSource v2 RAG search functions.
-- Semantic search: pgvector cosine similarity over rag_embeddings.
-- Lexical search: Postgres full-text search over rag_chunks.content.
-- These functions are intended for backend service-role RPC calls.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_fts
    ON rag_chunks USING gin (to_tsvector('english', content));

CREATE OR REPLACE FUNCTION match_rag_chunks(
    query_embedding vector(1536),
    match_limit INT DEFAULT 12,
    model_filter TEXT DEFAULT 'text-embedding-3-small'
)
RETURNS TABLE (
    chunk_id UUID,
    source_id UUID,
    url TEXT,
    title TEXT,
    chunk_index INT,
    content TEXT,
    content_hash TEXT,
    embedding_model TEXT,
    similarity DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.id,
        c.source_id,
        c.url,
        c.title,
        c.chunk_index,
        c.content,
        c.content_hash,
        e.embedding_model,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM rag_embeddings e
    JOIN rag_chunks c ON c.id = e.chunk_id
    WHERE e.embedding_model = model_filter
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_limit;
$$;

CREATE OR REPLACE FUNCTION search_rag_chunks_lexical(
    query_text TEXT,
    match_limit INT DEFAULT 12
)
RETURNS TABLE (
    chunk_id UUID,
    source_id UUID,
    url TEXT,
    title TEXT,
    chunk_index INT,
    content TEXT,
    content_hash TEXT,
    lexical_score REAL
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.id,
        c.source_id,
        c.url,
        c.title,
        c.chunk_index,
        c.content,
        c.content_hash,
        ts_rank(
            to_tsvector('english', c.content),
            websearch_to_tsquery('english', query_text)
        ) AS lexical_score
    FROM rag_chunks c
    WHERE to_tsvector('english', c.content)
          @@ websearch_to_tsquery('english', query_text)
    ORDER BY lexical_score DESC
    LIMIT match_limit;
$$;
