<#
.SYNOPSIS
    MedTrack ERP - One-Click Database Setup Script for Windows PowerShell
.DESCRIPTION
    Initializes or restores the MedTrack PostgreSQL database from db_scripts/medtrack_complete_dev.sql.
#>

param(
    [string]$HostName = "localhost",
    [string]$Port = "5432",
    [string]$User = "postgres",
    [string]$DbName = "medtrack",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "       MedTrack ERP - Database Setup Utility            " -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

# 1. Check for psql
$psqlCmd = Get-Command psql -ErrorAction SilentlyContinue
$psqlPath = if ($psqlCmd) { $psqlCmd.Source } else { $null }

if (-not $psqlPath) {
    # Check default PostgreSQL installation paths
    $pgVersions = @("17", "16", "15", "14")
    foreach ($v in $pgVersions) {
        $candidate = "C:\Program Files\PostgreSQL\$v\bin\psql.exe"
        if (Test-Path $candidate) {
            $psqlPath = $candidate
            break
        }
    }
}

if (-not $psqlPath) {
    Write-Host "[ERROR] PostgreSQL client 'psql' was not found in PATH or in 'C:\Program Files\PostgreSQL'." -ForegroundColor Red
    Write-Host "Please install PostgreSQL or add its 'bin' directory to your PATH." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/4] Found PostgreSQL client: $psqlPath" -ForegroundColor Green

# 2. Extract credentials from .env if present
if (Test-Path ".env") {
    $envLines = Get-Content ".env"
    foreach ($line in $envLines) {
        if ($line -match '^DATABASE_SYNC_URL=postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)$') {
            if (-not $User -or $User -eq "postgres") { $User = $matches[1] }
            if (-not $Password) { $Password = $matches[2] }
            if (-not $HostName -or $HostName -eq "localhost") { $HostName = $matches[3] }
            if ($matches[4]) { $Port = $matches[4] }
            if (-not $DbName -or $DbName -eq "medtrack") { $DbName = $matches[5] }
        }
    }
}

if (-not $Password) {
    $Password = $env:PGPASSWORD
}
if (-not $Password) {
    $Password = "123"
}

$env:PGPASSWORD = $Password

# 3. Create database if it does not exist
Write-Host "[2/4] Ensuring database '$DbName' exists on ${HostName}:${Port}..." -ForegroundColor Yellow

$dbCheckCmd = "& `"$psqlPath`" -h $HostName -p $Port -U $User -d postgres -tAc `"SELECT 1 FROM pg_database WHERE datname='$DbName' LIMIT 1;`""
$dbExists = Invoke-Expression $dbCheckCmd 2>$null

if ($dbExists.Trim() -ne "1") {
    Write-Host "      Database '$DbName' does not exist. Creating..." -ForegroundColor Yellow
    & "$psqlPath" -h $HostName -p $Port -U $User -d postgres -c "CREATE DATABASE `"$DbName`";"
    Write-Host "      Database '$DbName' created successfully." -ForegroundColor Green
} else {
    Write-Host "      Database '$DbName' already exists." -ForegroundColor Green
}

# 4. Apply complete dev SQL script
$sqlFile = Join-Path $PSScriptRoot "db_scripts\medtrack_complete_dev.sql"
if (-not (Test-Path $sqlFile)) {
    Write-Host "[ERROR] Could not find SQL script at: $sqlFile" -ForegroundColor Red
    exit 1
}

Write-Host "[3/4] Applying SQL script: $sqlFile..." -ForegroundColor Yellow
& "$psqlPath" -h $HostName -p $Port -U $User -d $DbName -f "$sqlFile" --quiet

# 5. Verify installation
Write-Host "[4/4] Verifying database structure..." -ForegroundColor Yellow
$tableCount = & "$psqlPath" -h $HostName -p $Port -U $User -d $DbName -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
$alembicRev = & "$psqlPath" -h $HostName -p $Port -U $User -d $DbName -tAc "SELECT version_num FROM alembic_version LIMIT 1;"

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host " [OK] Database Setup Completed Successfully!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host " Tables created   : $tableCount" -ForegroundColor Cyan
Write-Host " Alembic revision : $alembicRev" -ForegroundColor Cyan
Write-Host "`nYou are ready to run the backend and frontend!" -ForegroundColor White
Write-Host "  Backend  : python -m uvicorn backend.app.main:app --port 8001 --reload" -ForegroundColor Gray
Write-Host "  Frontend : cd frontend && npm run dev`n" -ForegroundColor Gray
