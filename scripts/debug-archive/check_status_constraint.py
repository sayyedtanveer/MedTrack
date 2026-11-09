#!/usr/bin/env python3
"""Check what status values are allowed by the database constraint."""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:123@localhost:5432/medtrack")


async def main():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        # Get constraint definition
        result = await conn.execute(text("""
            SELECT conname, pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'subcontract_orders'::regclass
            AND conname LIKE '%status%'
        """))
        
        print("Status constraints on subcontract_orders:")
        for row in result:
            print(f"\nConstraint: {row[0]}")
            print(f"Definition: {row[1]}")
        
        # Get current status values in use
        result = await conn.execute(text("""
            SELECT DISTINCT status 
            FROM subcontract_orders 
            WHERE is_deleted = false
            ORDER BY status
        """))
        
        print("\nCurrent status values in database:")
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  - '{row[0]}'")
        else:
            print("  (no records found)")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
