# Deployment Guide

This guide explains how to deploy the Investor-Report-Finder after the restructure to proper Python packaging.

---

## Project Structure

```
Investor-Report-Finder/
├── backend/                    # Python package
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── scraper.py
│   ├── prompt_parser.py
│   ├── cache_manager.py
│   ├── company_resolver.py
│   ├── ticker_parser.py
│   ├── financial_analyzer.py
│   ├── report_generator.py
│   ├── accounting_standards.py
│   └── pdf_parser.py
├── cli/                        # CLI package
│   ├── __init__.py
│   └── cli.py
├── frontend/                   # React/Vite frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── company_mapping.json
├── company_mapping_enhanced.json
├── requirements.txt
└── vercel.json
```

---

## Local Development

### Start Backend
```bash
cd Investor-Report-Finder
uvicorn backend.main:app --reload
```
Backend runs at: **http://localhost:8000**

### Start Frontend
```bash
cd Investor-Report-Finder/frontend
npm install
npm run dev
```
Frontend runs at: **http://localhost:5173**

### Run CLI
```bash
cd Investor-Report-Finder
python -m cli.cli "Find Apple 2023 annual report"
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
TAVILY_API_KEY=your_tavily_api_key
SERPER_API_KEY=your_serper_api_key
OPENAI_API_KEY=your_openai_api_key      # Optional
GOOGLE_API_KEY=your_google_api_key      # Optional
```

---

## Deployment Options

### Option 1: Vercel (Frontend + Serverless Backend)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Restructured to proper Python packaging"
   git push origin main
   ```

2. **Deploy on Vercel**
   - Import project from GitHub
   - Add environment variables in Vercel dashboard
   - The `vercel.json` configures the build

3. **Update vercel.json** for new structure:
   ```json
   {
     "builds": [
       {
         "src": "backend/main.py",
         "use": "@vercel/python"
       },
       {
         "src": "frontend/package.json",
         "use": "@vercel/static-build",
         "config": {
           "distDir": "dist"
         }
       }
     ],
     "routes": [
       { "src": "/api/(.*)", "dest": "backend/main.py" },
       { "src": "/(.*)", "dest": "frontend/$1" }
     ]
   }
   ```

> ⚠️ **Vercel Limitation**: Free tier has 10-second timeout. Consider Render/Railway for backend if scraping is needed.

---

### Option 2: Render (Recommended for Backend)

1. **Create requirements.txt** (already exists):
   ```
   fastapi
   uvicorn
   requests
   beautifulsoup4
   python-dotenv
   pydantic
   tavily-python
   openai
   google-generativeai
   ```

2. **Deploy Backend on Render**
   - Create new Web Service
   - Connect GitHub repo
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables

3. **Deploy Frontend on Vercel**
   - Update frontend API URL to point to Render backend

---

### Option 3: Docker

**Dockerfile** for backend:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run**:
```bash
docker build -t investor-finder .
docker run -p 8000:8000 --env-file .env investor-finder
```

---

### Option 4: Railway

1. Connect GitHub repository
2. Railway auto-detects Python
3. Set environment variables
4. Use start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

---

## Important Notes

### ASGI App Location
The FastAPI app is now at:
```
backend.main:app
```
**NOT** `main:app` (the old path).

### Import Structure
All imports use absolute paths:
```python
from backend.scraper import IRReportFinder
from backend.prompt_parser import PromptParser
from backend.company_resolver import get_resolver
```

### File Paths
Data files (`company_mapping.json`, `cache.db`) are in the project root.
The backend modules use `Path(__file__).parent.parent` to locate them.

### Cache Persistence
- **Local**: SQLite `cache.db` persists
- **Serverless**: Cache resets each request (consider external DB for production)

---

## Production Checklist

- [ ] Set all environment variables
- [ ] Update frontend API URL for production backend
- [ ] Configure CORS in `backend/main.py` for production domain
- [ ] Consider external database for caching (PostgreSQL/Redis)
- [ ] Set up monitoring/logging
