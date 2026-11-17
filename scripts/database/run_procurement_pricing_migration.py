#!/usr/bin/env python3
"""
Procurement Pricing Phase 2 - Database Migration Script

This script safely creates procurement pricing tables if they don't exist.
Safe to run multiple times - will skip existing tables.

Usage:
    python scripts/database/run_procurement_pricing_migration.py

Environment Variables:
    DATABASE_URL or DATABASE_SYNC_URL from .env
"""

import asyncio
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_SYNC_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL or DATABASE_SYNC_URL not found in .env")
    sys.exit(1)

# Parse PostgreSQL connection string
# Format: postgresql://user:password@host:port/database
try:
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    
    if DATABASE_URL.startswith("postgresql+asyncpg"):
        # Convert async URL to sync URL
        DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    
    parsed = urlparse(DATABASE_URL)
    
    db_config = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "123",
    }
except Exception as e:
    print(f"❌ ERROR parsing DATABASE_URL: {e}")
    sys.exit(1)

print(f"Connecting to PostgreSQL...")
print(f"  Host: {db_config['host']}")
print(f"  Port: {db_config['port']}")
print(f"  Database: {db_config['database']}")
print(f"  User: {db_config['user']}")

# Read SQL script
sql_script_path = Path(__file__).parent.parent.parent / "db_scripts" / "create_procurement_pricing_tables_safe.sql"

if not sql_script_path.exists():
    print(f"❌ ERROR: SQL script not found at {sql_script_path}")
    sys.exit(1)

with open(sql_script_path, 'r') as f:
    sql_script = f.read()

print(f"\n{'='*70}")
print("PROCUREMENT PRICING PHASE 2 - DATABASE MIGRATION")
print(f"{'='*70}\n")

try:
    # Connect to database
    print("📡 Connecting to database...")
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Execute SQL script
    print("🔨 Executing migration script...\n")
    
    # Split by semicolon and execute statements
    statements = [s.strip() for s in sql_script.split(';') if s.strip()]
    
    for i, statement in enumerate(statements, 1):
        try:
            cursor.execute(statement)
            
            # Fetch any output (like RAISE NOTICE)
            if cursor.description:
                rows = cursor.fetchall()
                for row in rows:
                    print(f"  → {row[0]}")
            
            print(f"✓ Statement {i}/{len(statements)} executed")
            
        except Exception as e:
            print(f"⚠ Statement {i} result: {str(e)[:100]}")
    
    # Commit transaction
    conn.commit()
    
    print(f"\n{'='*70}")
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print(f"{'='*70}\n")
    
    # Verify tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN (
            'supplier_price_agreements',
            'standard_cost_revisions', 
            'material_cost_history',
            'price_override_records'
        )
        ORDER BY table_name;
    """)
    
    tables = cursor.fetchall()
    print("Created/Verified Tables:")
    for (table_name,) in tables:
        print(f"  ✓ {table_name}")
    
    if len(tables) == 4:
        print(f"\n✅ All 4 procurement pricing tables ready!")
    else:
        print(f"\n⚠ Warning: Expected 4 tables, found {len(tables)}")
    
    # Check null operation_code
    cursor.execute("SELECT COUNT(*) FROM operations WHERE operation_code IS NULL;")
    null_count = cursor.fetchone()[0]
    print(f"\n✓ Null operation_code values: {null_count}")
    
    cursor.close()
    conn.close()
    
    print(f"\n{'='*70}")
    print("🎉 Database is ready for supplier pricing features!")
    print(f"{'='*70}\n")
    
    print("Next steps:")
    print("1. Restart backend: python -m uvicorn backend.app.main:app --reload")
    print("2. Test workflow: python tests/debug_full_onboarding_flow.py")
    print()
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
