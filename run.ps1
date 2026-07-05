# MedTrack Project - Single Command Launcher
# Run both Backend + Frontend with: .\run.ps1

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  MedTrack ERP - Full Stack Dev Mode" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory
Push-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Python command — prefer .venv, fall back to system python
if (Test-Path '.\.venv\Scripts\python.exe') {
    $pythonCmd = '.\.venv\Scripts\python.exe'
} else {
    $pythonCmd = 'python'
}

# Step 1: Start Backend (new terminal tab) — port 8001 matches vite proxy
Write-Host "[1/2] Starting Backend API on http://localhost:8001 ..." -ForegroundColor Blue
$backendArgs = "-NoExit", "-Command", "cd '$PWD'; $pythonCmd -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload"
Start-Process powershell -ArgumentList $backendArgs -WindowStyle Normal

# Wait for backend to start
Start-Sleep -Seconds 3

# Step 2: Start Frontend (new terminal tab) — Vite serves on port 3000
Write-Host "[2/2] Starting Frontend Dev Server on http://localhost:3000 ..." -ForegroundColor Blue
$frontendArgs = "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"
Start-Process powershell -ArgumentList $frontendArgs -WindowStyle Normal

# Wait for frontend to start
Start-Sleep -Seconds 5

# Display success message
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  ✅ All Services Started" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API  : http://localhost:8001" -ForegroundColor Yellow
Write-Host "  API Docs     : http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host "  Frontend     : http://localhost:3000" -ForegroundColor Yellow
Write-Host "  (Vite proxies /api → http://localhost:8001)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Login Credentials:" -ForegroundColor Yellow
Write-Host "  Email        : admin@medtrack-demo.com" -ForegroundColor Cyan
Write-Host "  Password     : Admin@1234" -ForegroundColor Cyan
Write-Host "  Tenant ID    : b5ef68c4-18be-4fa6-a439-a23c34877550" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Testing BOM:" -ForegroundColor Yellow
Write-Host "  Open another terminal and run:" -ForegroundColor Cyan
Write-Host "  python test_bom_api.py" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Pop-Location

Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

