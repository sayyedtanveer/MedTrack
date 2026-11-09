#!/usr/bin/env bash
# ==============================================================================
# MedTrack ERP - One-Click Database Setup Script (Linux / macOS / WSL)
# ==============================================================================
set -e

HOST="${PGHOST:-localhost}"
PORT="${PGPORT:-5432}"
USER="${PGUSER:-postgres}"
DBNAME="${PGDATABASE:-medtrack}"
PASSWORD="${PGPASSWORD:-123}"

echo ""
echo "========================================================"
echo "       MedTrack ERP - Database Setup Utility            "
echo "========================================================"
echo ""

# Extract credentials from .env if present
if [ -f ".env" ]; then
    DB_SYNC_URL=$(grep "^DATABASE_SYNC_URL=" .env | cut -d '=' -f2- || true)
    if [ -n "$DB_SYNC_URL" ]; then
        echo "Found DATABASE_SYNC_URL in .env"
    fi
fi

export PGPASSWORD="$PASSWORD"

echo "[1/3] Ensuring database '$DBNAME' exists on $HOST:$PORT..."
DB_EXISTS=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DBNAME' LIMIT 1;" 2>/dev/null || true)

if [ "$DB_EXISTS" != "1" ]; then
    echo "      Creating database '$DBNAME'..."
    psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -c "CREATE DATABASE \"$DBNAME\";"
    echo "      Database created successfully."
else
    echo "      Database '$DBNAME' already exists."
fi

SQL_FILE="./db_scripts/medtrack_complete_dev.sql"
if [ ! -f "$SQL_FILE" ]; then
    echo "[ERROR] Could not find SQL script at $SQL_FILE"
    exit 1
fi

echo "[2/3] Restoring database from $SQL_FILE..."
psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DBNAME" -f "$SQL_FILE" --quiet

echo "[3/3] Verifying database tables..."
TABLE_COUNT=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DBNAME" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
ALEMBIC_REV=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DBNAME" -tAc "SELECT version_num FROM alembic_version LIMIT 1;")

echo ""
echo "========================================================"
echo " [OK] Database Setup Completed Successfully!"
echo "========================================================"
echo " Tables created   : $TABLE_COUNT"
echo " Alembic revision : $ALEMBIC_REV"
echo ""
echo "You can now run:"
echo "  uvicorn backend.app.main:app --port 8001 --reload"
echo ""
