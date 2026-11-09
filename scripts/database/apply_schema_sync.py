#!/usr/bin/env python3
"""Apply missing columns to PostgreSQL database."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import settings

async def apply_schema_fixes():
    """Apply SQL script to add missing columns."""
    engine = create_async_engine(settings.async_database_url, echo=False)
    
    sql_statements = [
        # 1. inventory_transactions.batch_id
        "ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS batch_id UUID NULL;",
        
        # 2-5. batches table columns
        "ALTER TABLE batches ADD COLUMN IF NOT EXISTS original_quantity NUMERIC(18, 4) NULL;",
        "ALTER TABLE batches ADD COLUMN IF NOT EXISTS reserved_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0;",
        "ALTER TABLE batches ADD COLUMN IF NOT EXISTS consumed_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0;",
        "ALTER TABLE batches ADD COLUMN IF NOT EXISTS returned_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0;",
        
        # 6-13. job_cards table columns
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP WITH TIME ZONE NULL;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS total_downtime_seconds NUMERIC(15, 3) NOT NULL DEFAULT 0;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS pause_reason VARCHAR(255) NULL;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS operator_notes TEXT NULL;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS produced_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS scrap_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS rework_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS rejected_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0;",
        
        # 14-15. sales_order_lines table columns
        "ALTER TABLE sales_order_lines ADD COLUMN IF NOT EXISTS shortfall_quantity NUMERIC(18, 4) NOT NULL DEFAULT 0;",
        "ALTER TABLE sales_order_lines ADD COLUMN IF NOT EXISTS production_required BOOLEAN NOT NULL DEFAULT FALSE;",
        
        # 16-18. notifications table columns
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notification_type VARCHAR(50) NULL;",
        "UPDATE notifications SET notification_type = 'INFO' WHERE notification_type IS NULL;",
        "ALTER TABLE notifications ALTER COLUMN notification_type SET NOT NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS deep_link VARCHAR(500) NULL;",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS target_role VARCHAR(50) NULL;",
        "ALTER TABLE notifications ALTER COLUMN user_id DROP NOT NULL;",
    ]
    
    try:
        async with engine.begin() as conn:
            for idx, statement in enumerate(sql_statements, 1):
                try:
                    await conn.execute(text(statement))
                    print(f"✓ [{idx}/{len(sql_statements)}] Applied: {statement[:80]}")
                except Exception as e:
                    print(f"⚠ [{idx}/{len(sql_statements)}] Warning: {e}")
        
        print("\n✓ Schema sync completed successfully!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(apply_schema_fixes())
