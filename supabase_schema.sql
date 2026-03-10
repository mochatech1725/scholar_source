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

-- Verify the table was created successfully
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'jobs'
ORDER BY ordinal_position;

-- MIGRATION SCRIPT: Clean existing data for authentication upgrade
-- Run this separately AFTER backing up your data if needed
-- This implements the "start fresh" migration approach

-- Uncomment the line below to execute the migration:
-- TRUNCATE jobs CASCADE;
