@echo off
echo ===================================================
echo Starting Investor-Report-Finder App
echo ===================================================

echo [1/2] Starting Backend...
start "Backend Server" cmd /k "cd backend && .venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Starting Frontend...
cd frontend
if not exist node_modules (
    echo Node modules not found. Installing dependencies...
    call npm install
)
echo Starting Vite Dev Server...
npm run dev
