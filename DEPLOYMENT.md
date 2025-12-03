# Deployment Guide

This guide explains how to deploy the Investor-Report-Finder to Vercel.

## Prerequisites

- A GitHub account
- A Vercel account (free tier is sufficient)
- Git installed locally
- Your project code ready

## Step 1: Push to GitHub

1.  Initialize a Git repository in the `investor-report-finder` folder (if not already done):
    ```bash
    cd investor-report-finder
    git init
    git add .
    git commit -m "Initial commit"
    ```

2.  Create a new repository on GitHub (e.g., `Investor-Report-Finder`).

3.  Link your local repo to GitHub:
    ```bash
    git remote add origin https://github.com/nuwal01/Investor-Report-Finder
    git branch -M main
    git push -u origin main
    ```

## Step 2: Deploy to Vercel

1.  Go to the [Vercel Dashboard](https://vercel.com/dashboard).
2.  Click **"Add New..."** -> **"Project"**.
3.  Import the `investor-report-finder` repository you just created.
4.  **Configure Project**:
    *   **Framework Preset**: Vercel should detect `Vite` for the frontend. If not, select it.
    *   **Root Directory**: Leave as `./`.
    *   **Build Command**: `cd frontend && npm install && npm run build` (or rely on default if Vercel detects it).
        *   *Note*: Our `vercel.json` handles the build configuration, so you might not need to change much.
    *   **Environment Variables**: Add the following:
        *   `TAVILY_API_KEY`: Your Tavily API key.
        *   `OPENAI_API_KEY`: (Optional) If you use OpenAI.
        *   `GOOGLE_API_KEY`: (Optional) If you use Gemini.

5.  Click **"Deploy"**.

## Important Notes

### Serverless Function Timeouts
Vercel's free tier limits serverless functions (our Python backend) to **10 seconds**.
*   **Direct Search**: Searching via Tavily is fast and should work fine.
*   **Scraping**: If the app falls back to scraping, it enforces a 12-second rate limit delay. This **will cause a timeout** on Vercel's free tier.
*   **Solution**: For heavy scraping, consider deploying the backend to **Render** or **Railway**, which allow longer execution times.

### File Persistence
Vercel serverless functions are ephemeral. The `cache.db` (SQLite) file **will not persist** between requests.
*   Every request starts with a fresh, empty cache.
*   To enable persistent caching, you would need to switch to an external database like **PostgreSQL** (e.g., Vercel Postgres or Supabase).
