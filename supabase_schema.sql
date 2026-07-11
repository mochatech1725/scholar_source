-- ScholarSource Supabase Schema
-- Use this file to create a fresh ScholarSource database from scratch.
--
-- The RAG tables are intentionally explicit because they define the citation,
-- retrieval, and run-trace contract for ScholarSource v2.
--
-- Legacy note: older databases may still contain a course_cache table from the
-- v1 cache design. The current backend does not reference it, so fresh
-- databases do not create it here.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Existing async job table used by the current application.
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')),
    inputs JSONB NOT NULL,
    results JSONB,
    raw_output TEXT,
    error TEXT,
    status_message TEXT,
    search_title TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_user_created_at ON jobs(user_id, created_at DESC);

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own jobs" ON jobs;
DROP POLICY IF EXISTS "Users can create own jobs" ON jobs;
DROP POLICY IF EXISTS "Users can update own jobs" ON jobs;
DROP POLICY IF EXISTS "Users can delete own jobs" ON jobs;

CREATE POLICY "Users can view own jobs" ON jobs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own jobs" ON jobs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own jobs" ON jobs
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own jobs" ON jobs
    FOR DELETE USING (auth.uid() = user_id);

-- RAG run records. A run is created before the pipeline returns so every
-- generated recommendation can be traced back to queries, evidence, and models.
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

-- Source inventory. Source records are shared corpus data and should normally
-- be written/read by backend service-role code, not directly by browser clients.
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

-- Rejected candidates are stored per run so weak evidence and source-quality
-- decisions can be audited later.
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

-- Default vector size is 1536 for text-embedding-3-small. If the production
-- embedding model changes dimension, add a migration before writing new rows.
CREATE TABLE IF NOT EXISTS rag_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES rag_chunks(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL CHECK (embedding_dimensions > 0),
    embedding vector(1536) NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    UNIQUE (chunk_id, embedding_model),
    UNIQUE (content_hash, embedding_model)
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

-- Source quality policy rules (mirrors migrations/003). Not an
-- allowlist/blocklist pair: 'preferred' rows are a fast-accept list, and a
-- domain matching no row is still accepted by default checks. 'rejected' is
-- the only hard filter. A 'domain' rule matches the domain and its
-- subdomains; a 'suffix' rule matches any host ending with the pattern.
CREATE TABLE IF NOT EXISTS rag_domain_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern TEXT NOT NULL,
    match_type TEXT NOT NULL CHECK (match_type IN ('domain', 'suffix')),
    policy TEXT NOT NULL CHECK (policy IN ('rejected', 'preferred')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pattern, match_type)
);

CREATE INDEX IF NOT EXISTS idx_rag_domain_policies_policy
    ON rag_domain_policies(policy);

INSERT INTO rag_domain_policies (pattern, match_type, policy, reason) VALUES
    ('chegg.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('coursehero.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('studocu.com', 'domain', 'rejected', 'scraped-content aggregator'),
    ('scribd.com', 'domain', 'rejected', 'paywalled document aggregator'),
    ('numerade.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('bartleby.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('quizlet.com', 'domain', 'rejected', 'no extractable study text'),
    ('slideshare.net', 'domain', 'rejected', 'no extractable study text'),
    ('pinterest.com', 'domain', 'rejected', 'no extractable study text'),
    ('khanacademy.org', 'domain', 'preferred', 'open education source'),
    ('openstax.org', 'domain', 'preferred', 'open textbook publisher'),
    ('libretexts.org', 'domain', 'preferred', 'open textbook publisher'),
    ('ocw.mit.edu', 'domain', 'preferred', 'open courseware'),
    ('wikipedia.org', 'domain', 'preferred', 'open encyclopedia'),
    ('brilliant.org', 'domain', 'preferred', 'interactive courseware'),
    ('.edu', 'suffix', 'preferred', 'accredited US institution'),
    ('.gov', 'suffix', 'preferred', 'government publication'),
    ('.ac.uk', 'suffix', 'preferred', 'accredited UK institution')
ON CONFLICT (pattern, match_type) DO NOTHING;

ALTER TABLE rag_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_source_rejections ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_extracted_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_run_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_domain_policies ENABLE ROW LEVEL SECURITY;

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

-- No browser-client policies are defined for rag_sources,
-- rag_extracted_documents, rag_chunks, or rag_embeddings. These tables contain
-- shared corpus and retrieval internals and are intended for backend
-- service-role access unless a future reviewed API exposes them.
