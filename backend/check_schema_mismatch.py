#!/usr/bin/env python3
"""
Database Schema Sync Utility
=============================
Identifies and fixes schema mismatches between ORM models and actual database.

Usage:
    python check_schema_mismatch.py --fix     # Identify and fix mismatches
    python check_schema_mismatch.py --check   # Only check, don't fix
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import settings
from backend.app.infrastructure.persistence.database import Base

# Import every mapped model before reading Base.metadata. Without this the
# checker can report a false clean result while tables/columns are missing.
from backend.app.infrastructure.persistence.models import (  # noqa: F401
    tenant_model,
    user_model,
    audit_log_model,
    material_model,
    inventory_transaction_model,
    material_category_model,
    unit_of_measure_model,
    uom_conversion_model,
    location_model,
    batch_model,
    serial_number_model,
    item_template_model,
    item_variant_model,
    item_code_sequence_model,
    bom_model,
    workstation_model,
    operation_model,
    bom_operation_model,
    work_order_model,
    sales_models,
    quality_model,
    purchase_order_model,
    grn_model,
    supplier_model,
    po_sequence_model,
    material_request_model,
    mrp_model,
    subcontract_model,
    finance_models,
    inventory_management_models,
)
from backend.app.infrastructure.logging.models import ErrorLogModel  # noqa: F401


async def get_orm_columns(table) -> dict:
    """Get all columns defined in ORM model."""
    columns = {}
    for column in table.__table__.columns:
        columns[column.name] = {
            'type': str(column.type),
            'nullable': column.nullable,
            'default': column.default,
        }
    return columns


async def get_db_columns(engine, table_name: str) -> dict:
    """Get all columns in actual database table."""
    async with engine.begin() as conn:
        result = await conn.execute(text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """))
        
        columns = {}
        for row in result.fetchall():
            col_name, data_type, is_null = row
            columns[col_name] = {
                'type': data_type,
                'nullable': is_null == 'YES',
            }
        return columns


async def check_schema():
    """Check for schema mismatches."""
    engine = create_async_engine(settings.database_url, echo=False)
    
    mismatches = []
    
    # Get all models from metadata
    for table in Base.metadata.tables.values():
        table_name = table.name
        
        # Get columns from ORM and DB
        orm_cols = {}
        for column in table.columns:
            orm_cols[column.name] = column

        db_cols = await get_db_columns(engine, table_name)

        if not db_cols:
            mismatches.append({
                'table': table_name,
                'column': None,
                'type': None,
                'nullable': None,
                'default': None,
                'action': 'CREATE_TABLE',
            })
            continue
        
        # Find missing columns
        for col_name, col_obj in orm_cols.items():
            if col_name not in db_cols:
                col_type = str(col_obj.type)
                nullable = col_obj.nullable
                default = col_obj.default
                
                mismatches.append({
                    'table': table_name,
                    'column': col_name,
                    'type': col_type,
                    'nullable': nullable,
                    'default': default,
                    'action': 'ADD',
                })
    
    await engine.dispose()
    return mismatches


async def fix_schema(mismatches: List[dict]) -> None:
    """Apply fixes for schema mismatches."""
    engine = create_async_engine(settings.database_url, echo=False)

    if any(m['action'] == 'CREATE_TABLE' for m in mismatches):
        print("Creating missing tables with ORM metadata...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    for mismatch in mismatches:
        if mismatch['action'] == 'CREATE_TABLE':
            print(f"  [OK] Ensured table {mismatch['table']}")
            continue

        table = mismatch['table']
        column = mismatch['column']
        col_type = mismatch['type']
        nullable = mismatch['nullable']
        default = mismatch['default']
        
        # Build ALTER TABLE statement
        null_constraint = "NULL" if nullable else "NOT NULL"
        
        # Handle default values
        default_clause = ""
        if default:
            if isinstance(default, str):
                default_clause = f" DEFAULT '{default}'"
            else:
                default_clause = f" DEFAULT {default}"
        
        # Simplify PostgreSQL types
        if 'character varying' in col_type.lower():
            pg_type = 'VARCHAR(255)'
        elif 'timestamp' in col_type.lower():
            pg_type = 'TIMESTAMP WITH TIME ZONE'
        elif 'uuid' in col_type.lower():
            pg_type = 'UUID'
        elif 'integer' in col_type.lower():
            pg_type = 'INTEGER'
        elif 'boolean' in col_type.lower():
            pg_type = 'BOOLEAN'
        elif 'text' in col_type.lower():
            pg_type = 'TEXT'
        elif 'jsonb' in col_type.lower():
            pg_type = 'JSONB'
        else:
            pg_type = col_type
        
        sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {pg_type} {null_constraint}{default_clause}"
        
        print(f"Executing: {sql}")
        
        try:
            async with engine.begin() as conn:
                await conn.execute(text(sql))
            print(f"  [OK] Added {table}.{column}")
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    await engine.dispose()


async def main():
    parser = argparse.ArgumentParser(description="Check and fix database schema mismatches")
    parser.add_argument("--fix", action="store_true", help="Fix mismatches")
    parser.add_argument("--check", action="store_true", help="Only check, don't fix")
    
    args = parser.parse_args()
    
    print("Checking database schema...")
    print("=" * 70)
    
    mismatches = await check_schema()
    
    if not mismatches:
        print("No schema mismatches found!")
        return
    
    print(f"Found {len(mismatches)} mismatch(es):\n")
    
    for m in mismatches:
        print(f"  Missing: {m['table']}.{m['column']}")
        print(f"    Type: {m['type']}")
        print(f"    Nullable: {m['nullable']}")
        if m['default']:
            print(f"    Default: {m['default']}")
        print()
    
    if args.fix:
        print("Applying fixes...")
        print("=" * 70)
        await fix_schema(mismatches)
        print("\nSchema sync complete!")
    elif not args.check:
        print("Run with --fix to apply fixes, or --check to only check")
    else:
        print("Use --fix to apply these fixes")


if __name__ == "__main__":
    asyncio.run(main())
