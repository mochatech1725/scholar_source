-- ScholarSource Jobs Table Schema
-- Run this in Supabase SQL Editor to create the jobs table

-- Jobs table to store job status and results
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
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

-- Verify the table was created successfully
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'jobs'
ORDER BY ordinal_position;
