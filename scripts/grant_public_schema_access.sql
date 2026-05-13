-- Supabase Data API Grant Script
-- Required for new Supabase projects created after May 30 2025.
-- Starting that date, tables in the "public" schema are NOT exposed to the
-- Data API (PostgREST / supabase-js) by default and require explicit GRANTs.
--
-- Run this script in the Supabase SQL Editor for each environment
-- (production and development).
--
-- Safe to run on existing projects — GRANTs are idempotent.

-- ============================================================
-- Table: jobs
-- ============================================================

-- anon role: no access — jobs are always user-scoped.
-- (No GRANT for anon intentionally.)

-- authenticated role: full CRUD, constrained by RLS policies below.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.jobs
    TO authenticated;

-- service_role: full CRUD — used by the Celery worker to write job
-- status/results and by admin operations. Bypasses RLS by design.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.jobs
    TO service_role;

-- ============================================================
-- Row Level Security
-- Already enabled + policies already exist in supabase_schema.sql.
-- Included here as a safety net in case this script is run on a
-- fresh environment that only applied migrations, not the full schema.
-- ============================================================

ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

-- Users can read their own jobs.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'jobs'
          AND policyname = 'Users can view own jobs'
    ) THEN
        CREATE POLICY "Users can view own jobs"
            ON public.jobs
            FOR SELECT
            TO authenticated
            USING (auth.uid() = user_id);
    END IF;
END $$;

-- Users can create their own jobs.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'jobs'
          AND policyname = 'Users can create own jobs'
    ) THEN
        CREATE POLICY "Users can create own jobs"
            ON public.jobs
            FOR INSERT
            TO authenticated
            WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

-- Users can update their own jobs.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'jobs'
          AND policyname = 'Users can update own jobs'
    ) THEN
        CREATE POLICY "Users can update own jobs"
            ON public.jobs
            FOR UPDATE
            TO authenticated
            USING (auth.uid() = user_id);
    END IF;
END $$;

-- Users can delete their own jobs.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'jobs'
          AND policyname = 'Users can delete own jobs'
    ) THEN
        CREATE POLICY "Users can delete own jobs"
            ON public.jobs
            FOR DELETE
            TO authenticated
            USING (auth.uid() = user_id);
    END IF;
END $$;
