-- ScholarSource v2 — harden the RAG retrieval RPC functions.
--
-- Migration 002 created `match_rag_chunks` and `search_rag_chunks_lexical`
-- with PostgreSQL's default privileges, which grant EXECUTE to PUBLIC. On
-- Supabase that means the `anon` and `authenticated` roles could call them
-- through PostgREST. The corpus was protected only by the accident that
-- `rag_chunks` has row level security enabled with no policies, and that
-- accident does not survive the first policy anyone adds to those tables.
--
-- This migration re-declares both functions with:
--   * an explicit security-invoker marker,
--   * a pinned `search_path` so the body cannot be redirected by a caller's
--     session settings to attacker-controlled tables, operators, or
--     text-search configurations,
--   * a bounded `match_limit` so a single RPC call cannot ask for the whole
--     corpus (or a negative/NULL limit) in one round trip,
-- and then revokes EXECUTE from PUBLIC, `anon`, and `authenticated`, leaving
-- only the backend's `service_role`.
--
-- `extensions` is in the pinned search path because Supabase installs the
-- `vector` extension there; a self-hosted or local Postgres usually has it in
-- `public`. Listing both keeps the `<=>` operator resolvable on either.
--
-- Safe to re-run. The function signatures are unchanged, so CREATE OR REPLACE
-- keeps the existing objects and no DROP is required.

-- Retrieval RPCs must never return more than this many rows per call.
-- `RagSettings.retrieval_limit` and `RagSettings.lexical_limit` default to 12;
-- this ceiling is the database-side backstop, not the tuning knob.

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
SECURITY INVOKER
SET search_path = public, extensions, pg_temp
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
    LIMIT LEAST(GREATEST(COALESCE(match_limit, 12), 1), 100);
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
SECURITY INVOKER
SET search_path = public, extensions, pg_temp
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
    LIMIT LEAST(GREATEST(COALESCE(match_limit, 12), 1), 100);
$$;

-- Execute privileges. PUBLIC holds EXECUTE by default; Supabase additionally
-- grants it to `anon` and `authenticated` through default privileges, so
-- revoking from PUBLIC alone is not enough.
REVOKE ALL ON FUNCTION match_rag_chunks(vector(1536), INT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION search_rag_chunks_lexical(TEXT, INT) FROM PUBLIC;

DO $$
DECLARE
    target_role TEXT;
BEGIN
    FOREACH target_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = target_role) THEN
            EXECUTE format(
                'REVOKE ALL ON FUNCTION match_rag_chunks(vector(1536), INT, TEXT) FROM %I',
                target_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION search_rag_chunks_lexical(TEXT, INT) FROM %I',
                target_role
            );
        END IF;
    END LOOP;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION match_rag_chunks(vector(1536), INT, TEXT) TO service_role;
        GRANT EXECUTE ON FUNCTION search_rag_chunks_lexical(TEXT, INT) TO service_role;
    END IF;
END $$;
