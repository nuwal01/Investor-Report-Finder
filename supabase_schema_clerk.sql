-- ============================================
-- Investor Report Finder - Supabase Schema (Clerk Auth)
-- ============================================
-- Run this SQL in your Supabase Dashboard > SQL Editor
-- This schema uses Clerk user IDs (clerk_user_id) instead of Supabase Auth
-- Safe to run multiple times - handles existing objects

-- ============================================
-- Reports Table
-- ============================================

CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id TEXT NOT NULL,
    company_name TEXT NOT NULL,
    ticker TEXT,
    year INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    file_url TEXT NOT NULL,
    source_url TEXT,
    title TEXT,
    status TEXT DEFAULT 'found',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast user queries
CREATE INDEX IF NOT EXISTS idx_reports_clerk_user_id ON public.reports(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_reports_company ON public.reports(company_name);
CREATE INDEX IF NOT EXISTS idx_reports_ticker ON public.reports(ticker);

-- ============================================
-- Search History Table
-- ============================================

CREATE TABLE IF NOT EXISTS public.search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast user queries
CREATE INDEX IF NOT EXISTS idx_search_history_clerk_user_id ON public.search_history(clerk_user_id);

-- ============================================
-- User Settings Table
-- ============================================

CREATE TABLE IF NOT EXISTS public.user_settings (
    clerk_user_id TEXT PRIMARY KEY,
    openai_api_key TEXT,
    openrouter_api_key TEXT,
    serper_api_key TEXT,
    tavily_api_key TEXT,
    openai_provider TEXT CHECK (openai_provider IN ('openai', 'openrouter')) DEFAULT 'openai',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Trigger for auto-updating updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to reports table
DROP TRIGGER IF EXISTS update_reports_updated_at ON public.reports;
CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON public.reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to user_settings table
DROP TRIGGER IF EXISTS update_user_settings_updated_at ON public.user_settings;
CREATE TRIGGER update_user_settings_updated_at
    BEFORE UPDATE ON public.user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Row Level Security (Service Key bypasses RLS)
-- ============================================
-- Note: When using service_role key from backend, RLS is bypassed.
-- The backend enforces user isolation via clerk_user_id in queries.
-- If you want additional security, uncomment and configure RLS below.

-- ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.search_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

-- ============================================
-- Verification Queries (Run after setup)
-- ============================================

-- Check tables exist:
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' AND table_name IN ('reports', 'search_history', 'user_settings');

-- Check reports table structure:
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'reports';

-- Test insert (replace with actual clerk_user_id):
-- INSERT INTO public.reports (clerk_user_id, company_name, ticker, year, report_type, file_url)
-- VALUES ('user_123', 'Apple Inc.', 'AAPL', 2023, 'Annual Report', 'https://example.com/report.pdf');

-- Check data:
-- SELECT * FROM public.reports LIMIT 5;
