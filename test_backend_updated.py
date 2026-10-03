"""Quick test to verify backend has the new consumption logic"""
import sys
sys.path.insert(0, 'backend')

import asyncio
from sqlalchemy import text, select
from app.infrastructure.persistence.database import get_engine

async def check_backend():
    engine = get_engine()
    
    async with engine.begin() as conn:
        # Check if consumed_quantity column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='subcontract_order_lines' 
            AND column_name='consumed_quantity'
        """))
        
        col_exists = result.first()
        
        if col_exists:
            print("✅ consumed_quantity column exists")
            
            # Check if any consumption has happened
            result = await conn.execute(text("""
                SELECT 
                    COUNT(*) as total_lines,
                    SUM(CASE WHEN consumed_quantity > 0 THEN 1 ELSE 0 END) as lines_with_consumption,
                    MAX(consumed_quantity) as max_consumed
                FROM subcontract_order_lines
            """))
            
            row = result.first()
            print(f"   Total order lines: {row.total_lines}")
            print(f"   Lines with consumption: {row.lines_with_consumption}")
            print(f"   Max consumed: {row.max_consumed}")
            
            if row.lines_with_consumption > 0:
                print("✅ Consumption logic is working!")
            else:
                print("⚠️  No consumption recorded yet. Try receiving a subcontract order.")
        else:
            print("❌ consumed_quantity column NOT found!")
            print("   Run: ALTER TABLE subcontract_order_lines ADD COLUMN consumed_quantity NUMERIC(15,3) DEFAULT 0;")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_backend())
