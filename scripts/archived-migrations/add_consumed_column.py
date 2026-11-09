"""Direct SQL execution to add consumed_quantity column"""
import sys
sys.path.insert(0, 'backend')

import asyncio
from sqlalchemy import text
from app.infrastructure.persistence.database import get_engine

async def main():
    engine = get_engine()
    
    async with engine.begin() as conn:
        # Check if exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='subcontract_order_lines' 
            AND column_name='consumed_quantity'
        """))
        
        if result.first():
            print("✓ Column consumed_quantity already exists")
            return
        
        # Add column
        await conn.execute(text("""
            ALTER TABLE subcontract_order_lines
            ADD COLUMN consumed_quantity NUMERIC(15,3) NOT NULL DEFAULT 0
        """))
        
        print("✓ Successfully added consumed_quantity column to subcontract_order_lines")
        
        # Verify
        result = await conn.execute(text("""
            SELECT column_name, data_type, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name='subcontract_order_lines'
            AND column_name='consumed_quantity'
        """))
        
        row = result.first()
        if row:
            print(f"✓ Verified: {row.column_name} {row.data_type}({row.numeric_precision},{row.numeric_scale})")

if __name__ == "__main__":
    asyncio.run(main())
