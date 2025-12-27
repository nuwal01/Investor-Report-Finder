# Supabase Setup Instructions

## Prerequisites

Before running the application, you need to set up Supabase for authentication and database storage.

## Step 1: Create a Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Click "Start your project" and sign up/sign in
3. Click "New project"
4. Fill in the project details:
   - **Name**: investor-report-finder (or your preferred name)
   - **Database Password**: Choose a strong password
   - **Region**: Select the closest region to your users
5. Wait for the project to be created (~2 minutes)

## Step 2: Get Your API Keys

1. In your Supabase project dashboard, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL**: `https://your-project.supabase.co`
   - **anon/public key**: A long string starting with `eyJ...`

## Step 3: Configure Environment Variables

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Create a `.env` file (copy from `.env.example` if you prefer):
   ```bash
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key-here
   VITE_API_URL=http://localhost:8000
   ```

3. Replace the values with your actual Supabase credentials from Step 2

## Step 4: Set Up Database Schema

1. In your Supabase dashboard, go to **SQL Editor**
2. Click "New query"
3. Copy the entire content from `supabase_schema.sql` (in the project root)
4. Paste it into the SQL Editor
5. Click "Run" or press `Ctrl+Enter`
6. Verify the table was created:
   - Go to **Table Editor**
   - You should see `user_api_keys` table

## Step 5: Enable Email Authentication

1. In Supabase dashboard, go to **Authentication** → **Providers**
2. Ensure "Email" is enabled (it should be by default)
3. (Optional) Configure email templates in **Authentication** → **Email Templates**

## Step 6: Configure Row Level Security (RLS)

The SQL script in Step 4 already enables RLS. To verify:

1. Go to **Authentication** → **Policies** in your Supabase dashboard
2. Select the `user_api_keys` table
3. You should see 4 policies:
   - Users can view own keys
   - Users can insert own keys
   - Users can update own keys
   - Users can delete own keys

If these don't exist, re-run the SQL script from Step 4.

## Step 7: Install Dependencies and Run

1. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:5173 in your browser

## Step 8: Create Your First Account

1. Click "Sign Up" on the landing page
2. Enter your email and password (minimum 6 characters)
3. Check your email for verification (if enabled in Supabase settings)
4. Sign in with your credentials
5. Click **⚙️ Settings** to configure your API keys
6. Start searching for investor reports!

## Troubleshooting

### "Missing Supabase environment variables" error
- Make sure your `.env` file exists in the `frontend` directory
- Check that the variable names start with `VITE_`
- Restart the development server after changing `.env`

### "Error loading settings" after sign in
- Verify the database schema was created correctly (Step 4)
- Check RLS policies are enabled (Step 6)
- Look at browser console for detailed error messages

### Email verification not working
- Go to Supabase Dashboard → **Authentication** → **Email Templates**
- Make sure email confirmation is enabled
- For development, you can disable email confirmation: **Authentication** → **Settings** → Disable "Enable email confirmations"

### Can't sign in/sign up
- Check Supabase dashboard → **Authentication** → **Users** to see if the user was created
- Verify your Supabase credentials are correct in `.env`
- Check browser console for errors

## Next Steps

Once set up:
- Configure your API keys (OpenAI/OpenRouter and Serper) in Settings
- Start searching for investor reports using natural language
- Your API keys are securely stored in Supabase with RLS protection

## Security Notes

- Never commit your `.env` file to version control
- The anon key is safe to use in the frontend (it's intended for public use)
- Row Level Security ensures users can only access their own data
- API keys are stored in your Supabase database, not in browser localStorage
