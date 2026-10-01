#!/usr/bin/env python3
"""Fix the subcontract_orders status constraint to match the model."""
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
        print("Dropping old status constraint...")
        await conn.execute(text("""
            ALTER TABLE subcontract_orders 
            DROP CONSTRAINT IF EXISTS subcontract_orders_status_check
        """))
        
        print("Adding new status constraint with correct values...")
        await conn.execute(text("""
            ALTER TABLE subcontract_orders 
            ADD CONSTRAINT subcontract_orders_status_check 
            CHECK (status IN (
                'draft', 
                'approved', 
                'materials_issued', 
                'partially_received', 
                'completed', 
                'cancelled'
            ))
        """))
        
        print("✅ Constraint updated successfully!")
        print("\nAllowed status values:")
        print("  - draft")
        print("  - approved")
        print("  - materials_issued")
        print("  - partially_received")
        print("  - completed")
        print("  - cancelled")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
