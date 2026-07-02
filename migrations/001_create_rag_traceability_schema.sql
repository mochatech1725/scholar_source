-- ScholarSource v2 RAG Traceability Schema
-- Incremental migration for an existing database that already has jobs.
--
-- Keep this migration aligned with the RAG portion of supabase_schema.sql so
-- fresh installs and upgraded installs end up with the same schema.
--
-- Legacy note: this migration intentionally does not drop, rename, or reuse any
-- existing course_cache table. v2 source/extraction/chunk/embedding tables are
-- the new cacheable retrieval substrate.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS rag_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    trace_key TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    normalized_input TEXT NOT NULL,
    normalized_input_hash TEXT NOT NULL,
    generated_queries JSONB NOT NULL DEFAULT '[]'::JSONB,
    candidate_source_urls JSONB NOT NULL DEFAULT '[]'::JSONB,
    accept_reject_reasons JSONB NOT NULL DEFAULT '[]'::JSONB,
    extraction_status JSONB NOT NULL DEFAULT '{}'::JSONB,
    chunk_ids UUID[] NOT NULL DEFAULT '{}'::UUID[],
    retrieval_scores JSONB NOT NULL DEFAULT '[]'::JSONB,
    rerank_order JSONB NOT NULL DEFAULT '[]'::JSONB,
    final_selected_evidence JSONB NOT NULL DEFAULT '[]'::JSONB,
    final_cited_source_ids UUID[] NOT NULL DEFAULT '{}'::UUID[],
    weak_evidence_status TEXT NOT NULL DEFAULT 'not_evaluated'
        CHECK (weak_evidence_status IN ('not_evaluated', 'strong', 'weak', 'insufficient')),
    weak_evidence_reason TEXT,
    model_name TEXT,
    prompt_version TEXT,
    step_timings JSONB NOT NULL DEFAULT '{}'::JSONB,
    token_usage JSONB NOT NULL DEFAULT '{}'::JSONB,
    provider_cost JSONB NOT NULL DEFAULT '{}'::JSONB,
    failure_state JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CHECK (user_id IS NOT NULL OR trace_key IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_rag_runs_job_id ON rag_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_rag_runs_user_created_at ON rag_runs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_runs_status ON rag_runs(status);
CREATE INDEX IF NOT EXISTS idx_rag_runs_normalized_input_hash ON rag_runs(normalized_input_hash);

CREATE TABLE IF NOT EXISTS rag_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    quality_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (quality_status IN ('pending', 'accepted', 'rejected', 'needs_review')),
    quality_reason TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    UNIQUE (normalized_url)
);

CREATE INDEX IF NOT EXISTS idx_rag_sources_normalized_url ON rag_sources(normalized_url);
CREATE INDEX IF NOT EXISTS idx_rag_sources_quality_status ON rag_sources(quality_status);
CREATE INDEX IF NOT EXISTS idx_rag_sources_source_type ON rag_sources(source_type);

CREATE TABLE IF NOT EXISTS rag_source_rejections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES rag_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_rag_source_rejections_run_id ON rag_source_rejections(run_id);
CREATE INDEX IF NOT EXISTS idx_rag_source_rejections_normalized_url ON rag_source_rejections(normalized_url);

CREATE TABLE IF NOT EXISTS rag_extracted_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES rag_sources(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    extracted_text_hash TEXT NOT NULL,
    extraction_status TEXT NOT NULL
        CHECK (extraction_status IN ('pending', 'completed', 'failed', 'skipped')),
    extraction_error TEXT,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    UNIQUE (source_id, extracted_text_hash)
);

CREATE INDEX IF NOT EXISTS idx_rag_extracted_documents_source_id ON rag_extracted_documents(source_id);
CREATE INDEX IF NOT EXISTS idx_rag_extracted_documents_hash ON rag_extracted_documents(extracted_text_hash);
CREATE INDEX IF NOT EXISTS idx_rag_extracted_documents_status ON rag_extracted_documents(extraction_status);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES rag_sources(id) ON DELETE CASCADE,
    extracted_document_id UUID REFERENCES rag_extracted_documents(id) ON DELETE SET NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    token_count INTEGER CHECK (token_count IS NULL OR token_count >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, chunk_index, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_source_id ON rag_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id ON rag_chunks(extracted_document_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_hash ON rag_chunks(content_hash);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_model ON rag_chunks(embedding_model);

CREATE TABLE IF NOT EXISTS rag_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES rag_chunks(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL CHECK (embedding_dimensions > 0),
    embedding vector(1536) NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    UNIQUE (chunk_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_rag_embeddings_chunk_id ON rag_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_content_model ON rag_embeddings(content_hash, embedding_model);
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_vector_hnsw
    ON rag_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS rag_run_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES rag_runs(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    step_order INTEGER NOT NULL CHECK (step_order >= 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    input_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
    output_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_rag_run_steps_run_order ON rag_run_steps(run_id, step_order);
CREATE INDEX IF NOT EXISTS idx_rag_run_steps_status ON rag_run_steps(status);

ALTER TABLE rag_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_source_rejections ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_extracted_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_run_steps ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own rag runs" ON rag_runs;
DROP POLICY IF EXISTS "Users can create own rag runs" ON rag_runs;
DROP POLICY IF EXISTS "Users can update own rag runs" ON rag_runs;
DROP POLICY IF EXISTS "Users can delete own rag runs" ON rag_runs;
DROP POLICY IF EXISTS "Users can view own rag run steps" ON rag_run_steps;
DROP POLICY IF EXISTS "Users can create own rag run steps" ON rag_run_steps;
DROP POLICY IF EXISTS "Users can update own rag run steps" ON rag_run_steps;
DROP POLICY IF EXISTS "Users can view own source rejections" ON rag_source_rejections;
DROP POLICY IF EXISTS "Users can create own source rejections" ON rag_source_rejections;

CREATE POLICY "Users can view own rag runs" ON rag_runs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own rag runs" ON rag_runs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own rag runs" ON rag_runs
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own rag runs" ON rag_runs
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own rag run steps" ON rag_run_steps
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM rag_runs
            WHERE rag_runs.id = rag_run_steps.run_id
              AND rag_runs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create own rag run steps" ON rag_run_steps
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1
            FROM rag_runs
            WHERE rag_runs.id = rag_run_steps.run_id
              AND rag_runs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update own rag run steps" ON rag_run_steps
    FOR UPDATE USING (
        EXISTS (
            SELECT 1
            FROM rag_runs
            WHERE rag_runs.id = rag_run_steps.run_id
              AND rag_runs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view own source rejections" ON rag_source_rejections
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM rag_runs
            WHERE rag_runs.id = rag_source_rejections.run_id
              AND rag_runs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create own source rejections" ON rag_source_rejections
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1
            FROM rag_runs
            WHERE rag_runs.id = rag_source_rejections.run_id
              AND rag_runs.user_id = auth.uid()
        )
    );
