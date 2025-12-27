    -- ============================================
    -- Investor Report Finder - Supabase Schema
    -- ============================================
    -- Run this SQL in your Supabase Dashboard > SQL Editor
    -- Safe to run multiple times - handles existing objects

    -- Drop existing policies first (if re-running)
    DO $$ 
    BEGIN
        DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
        DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
        DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
        DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;
    EXCEPTION
        WHEN undefined_table THEN
            NULL; -- Table doesn't exist yet, that's fine
    END $$;

    -- Create table for storing user API keys
    CREATE TABLE IF NOT EXISTS public.user_api_keys (
        user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
        openai_api_key TEXT,
        openrouter_api_key TEXT,
        serper_api_key TEXT,
        tavily_api_key TEXT,
        openai_provider TEXT CHECK (openai_provider IN ('openai', 'openrouter')) DEFAULT 'openai',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Create index on user_id for faster queries
    CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_id ON public.user_api_keys(user_id);

    -- Enable Row Level Security
    ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

    -- RLS Policy: Users can view their own API keys
    CREATE POLICY "Users can view own keys"
        ON public.user_api_keys
        FOR SELECT
        USING (auth.uid() = user_id);

    -- RLS Policy: Users can insert their own API keys
    CREATE POLICY "Users can insert own keys"
        ON public.user_api_keys
        FOR INSERT
        WITH CHECK (auth.uid() = user_id);

    -- RLS Policy: Users can update their own API keys
    CREATE POLICY "Users can update own keys"
        ON public.user_api_keys
        FOR UPDATE
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id);

    -- RLS Policy: Users can delete their own API keys
    CREATE POLICY "Users can delete own keys"
        ON public.user_api_keys
        FOR DELETE
        USING (auth.uid() = user_id);

    -- Create function to automatically update updated_at timestamp
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Create trigger to auto-update updated_at
    DROP TRIGGER IF EXISTS update_user_api_keys_updated_at ON public.user_api_keys;
    CREATE TRIGGER update_user_api_keys_updated_at
        BEFORE UPDATE ON public.user_api_keys
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();

    -- ============================================
    -- Verification Queries (Optional)
    -- ============================================
    -- Uncomment and run these to verify setup:

    -- Check if table exists and view structure:
    -- SELECT column_name, data_type, is_nullable 
    -- FROM information_schema.columns 
    -- WHERE table_name = 'user_api_keys';

    -- Check RLS is enabled:
    -- SELECT tablename, rowsecurity 
    -- FROM pg_tables 
    -- WHERE tablename = 'user_api_keys';

    -- View all policies:
    -- SELECT schemaname, tablename, policyname, cmd 
    -- FROM pg_policies 
    -- WHERE tablename = 'user_api_keys';

    -- Check your data (when signed in):
    -- SELECT user_id, openai_provider, created_at, updated_at 
    -- FROM public.user_api_keys;
