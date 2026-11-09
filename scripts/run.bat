@echo off
REM MedTrack - Run Backend + Frontend in One Terminal
REM This script starts both services concurrently

echo.
echo ==========================================
echo   MedTrack ERP - Full Stack Development
echo ==========================================
echo.

REM Check if .venv exists
if not exist ".\.venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
)

REM Activate Python environment
call .\.venv\Scripts\activate.bat

REM Start Backend on port 8001 (matches Vite proxy target)
echo.
echo [1/2] Starting Backend API on http://localhost:8001
start "MedTrack Backend" cmd /k "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload"

REM Wait for backend to start
timeout /t 3 /nobreak

REM Start Frontend
echo.
echo [2/2] Starting Frontend Dev Server
start "MedTrack Frontend" cmd /k "cd frontend && npm run dev"

REM Wait for frontend
timeout /t 5 /nobreak

echo.
echo ==========================================
echo   ✅ Services Started
echo ==========================================
echo.
echo   Backend API  : http://localhost:8001
echo   API Docs     : http://localhost:8001/docs
echo   Frontend     : http://localhost:3000
echo   (Vite proxies /api -^> http://localhost:8001)
echo.
echo   Login with:
echo   Email     : admin@medtrack-demo.com
echo   Password  : Admin@1234
echo   Tenant ID : b5ef68c4-18be-4fa6-a439-a23c34877550
echo.
echo   To test BOM, open another terminal:
echo   python test_bom_api.py
echo.
echo ==========================================
echo.
pause
