-- ScholarSource Jobs Table Schema
-- Run this in Supabase SQL Editor to create the jobs table

-- Jobs table to store job status and results
CREATE TABLE jobs (
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for faster lookups
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);

-- Enable Row Level Security
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- User-scoped RLS policies
CREATE POLICY "Users can view own jobs" ON jobs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own jobs" ON jobs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own jobs" ON jobs
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own jobs" ON jobs
    FOR DELETE USING (auth.uid() = user_id);

-- Course Analysis Cache Table
-- Stores cached course analysis results to avoid re-running expensive operations
-- Supports two cache types:
--   - 'analysis': Course analysis only (textbook extraction, topics) - TTL: 30 days
--   - 'full': Complete results including resources - TTL: 7 days
CREATE TABLE course_cache (
    cache_key TEXT PRIMARY KEY,  -- Format: "analysis:hash" or "full:hash"
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
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

-- User-scoped RLS policies
CREATE POLICY "Users can view own cache" ON course_cache
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own cache" ON course_cache
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own cache" ON course_cache
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own cache" ON course_cache
    FOR DELETE USING (auth.uid() = user_id);

-- Verify the tables were created successfully
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('jobs', 'course_cache')
ORDER BY table_name, ordinal_position;

-- MIGRATION SCRIPT: Clean existing data for authentication upgrade
-- Run this separately AFTER backing up your data if needed
-- This implements the "start fresh" migration approach

-- Uncomment the lines below to execute the migration:
-- TRUNCATE jobs CASCADE;
-- TRUNCATE course_cache CASCADE;
