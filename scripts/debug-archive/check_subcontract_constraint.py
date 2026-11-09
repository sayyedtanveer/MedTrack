#!/usr/bin/env python3
"""Check the subcontract_orders status constraint."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import text
from backend.app.infrastructure.database import engine


async def main():
    async with engine.begin() as conn:
        # Get constraint definition
        result = await conn.execute(text("""
            SELECT conname, pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'subcontract_orders'::regclass
            AND conname LIKE '%status%'
        """))
        
        print("Status constraints:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
        
        # Get current valid values
        result = await conn.execute(text("""
            SELECT DISTINCT status 
            FROM subcontract_orders 
            WHERE is_deleted = false
            ORDER BY status
        """))
        
        print("\nCurrent status values in use:")
        for row in result:
            print(f"  - {row[0]}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
