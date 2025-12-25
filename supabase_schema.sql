-- ScholarSource Jobs Table Schema
-- Run this in Supabase SQL Editor to create the jobs table

-- Jobs table to store job status and results
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    inputs JSONB NOT NULL,
    results JSONB,
    raw_output TEXT,
    error TEXT,
    status_message TEXT,
    search_title TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for faster lookups
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);

-- Enable Row Level Security
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations (public access for MVP)
-- This allows anyone to read/write jobs without authentication
-- You can restrict this later when you add user authentication
CREATE POLICY "Enable all access for jobs" ON jobs
    FOR ALL USING (true);

-- Course Analysis Cache Table
-- Stores cached course analysis results to avoid re-running expensive operations
-- Supports two cache types:
--   - 'analysis': Course analysis only (textbook extraction, topics) - TTL: 30 days
--   - 'full': Complete results including resources - TTL: 7 days
CREATE TABLE course_cache (
    cache_key TEXT PRIMARY KEY,  -- Format: "analysis:hash" or "full:hash"
    config_hash TEXT NOT NULL,   -- Hash of agents.yaml + tasks.yaml for auto-invalidation
    cache_type TEXT NOT NULL DEFAULT 'analysis',  -- 'analysis' or 'full'
    inputs JSONB NOT NULL,        -- Original inputs for debugging/auditing
    results JSONB NOT NULL,       -- Cached results
    cached_at TIMESTAMPTZ DEFAULT NOW()  -- Used for TTL expiration
);

-- Indexes for faster lookups
CREATE INDEX idx_course_cache_config_hash ON course_cache(config_hash);
CREATE INDEX idx_course_cache_cached_at ON course_cache(cached_at DESC);

-- Enable Row Level Security
ALTER TABLE course_cache ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations (public access for MVP)
CREATE POLICY "Enable all access for course_cache" ON course_cache
    FOR ALL USING (true);

-- Verify the tables were created successfully
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('jobs', 'course_cache')
ORDER BY table_name, ordinal_position;
