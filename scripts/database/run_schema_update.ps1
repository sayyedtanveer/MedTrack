# PowerShell Script to Run PostgreSQL Schema Update

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "PostgreSQL Manual Schema Update" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Database connection details
$dbHost = "localhost"
$dbPort = 5432
$dbUser = "medtrack_user"
$dbName = "medtrack_db"

Write-Host "Database: $dbHost`:$dbPort/$dbName" -ForegroundColor Yellow
Write-Host "User: $dbUser" -ForegroundColor Yellow
Write-Host ""

# Check if psql is available
try {
    $psqlVersion = psql --version
    Write-Host "Found PostgreSQL client: $psqlVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: psql not found. Please install PostgreSQL client tools." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Executing schema update SQL..." -ForegroundColor Yellow
Write-Host ""

# Run the SQL script
# Note: You may be prompted for password if not in .pgpass file
psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -f schema_update_manual.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Green
    Write-Host "SUCCESS! Schema updated successfully" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Red
    Write-Host "ERROR! Schema update failed" -ForegroundColor Red
    Write-Host "======================================" -ForegroundColor Red
    exit 1
}
