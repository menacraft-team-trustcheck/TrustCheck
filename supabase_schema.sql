-- ══════════════════════════════════════════════════════════════
-- MENACRAFT TRUSTCHECK — Supabase Schema
-- ══════════════════════════════════════════════════════════════
-- Run this in the Supabase SQL Editor to set up your tables.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Analyses Table ─────────────────────────────────────────
-- Stores every analysis run with full JSON results
CREATE TABLE IF NOT EXISTS analyses (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    file_hash   TEXT NOT NULL,
    filename    TEXT NOT NULL,
    analysis_type TEXT NOT NULL CHECK (analysis_type IN ('image', 'video', 'batch', 'audio')),
    results     JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookup by file hash
CREATE INDEX IF NOT EXISTS idx_analyses_file_hash ON analyses (file_hash);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses (created_at DESC);

-- ─── Reports Table ──────────────────────────────────────────
-- Stores generated PDF certificate metadata
CREATE TABLE IF NOT EXISTS reports (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    file_hash   TEXT NOT NULL,
    filename    TEXT NOT NULL,
    report_url  TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_file_hash ON reports (file_hash);

-- ─── Row Level Security (RLS) ───────────────────────────────
-- For a hackathon, we'll use service-role key so RLS is permissive.
-- In production, add proper policies.
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "service_role_all_analyses" ON analyses
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_reports" ON reports
    FOR ALL USING (true) WITH CHECK (true);

-- ─── Storage Buckets ────────────────────────────────────────
-- Create these in the Supabase Dashboard > Storage:
--   1. "uploads"  — for original uploaded images/videos
--   2. "reports"  — for generated PDF certificates
--   3. "heatmaps" — for heatmap overlay images
-- Set them to public if you want direct URL access from the frontend.
CREATE TABLE IF NOT EXISTS public.analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_hash TEXT NOT NULL,
    filename TEXT,
    analysis_type TEXT,
    results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_hash TEXT NOT NULL,
    filename TEXT,
    report_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);
