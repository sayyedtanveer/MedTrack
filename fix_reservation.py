import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import get_settings

async def main():
    engine = create_async_engine(get_settings().async_database_url)
    async with engine.begin() as conn:
        # Find the FG material ID for this SO line
        res = await conn.execute(text("""
            SELECT sol.product_id, so.tenant_id 
            FROM sales_order_lines sol
            JOIN sales_orders so ON sol.sales_order_id = so.id
            WHERE sol.id = 'c7c8d198-17b8-4fac-9a7b-40ea353726e2'
        """))
        row = res.fetchone()
        if not row:
            print("SO Line not found")
            return
            
        product_id = row[0]
        tenant_id = row[1]
        
        # Resolve to finished material
        res = await conn.execute(text(f"SELECT id FROM materials WHERE id = '{product_id}'"))
        mat_row = res.fetchone()
        
        if not mat_row:
            res = await conn.execute(text(f"SELECT material_id FROM item_variants WHERE id = '{product_id}'"))
            mat_row = res.fetchone()
            
        if not mat_row or not mat_row[0]:
            print("Material not found")
            return
            
        material_id = mat_row[0]
        
        # Check if reserve transaction already exists
        res = await conn.execute(text(f"SELECT id FROM inventory_transactions WHERE reference_id = 'c7c8d198-17b8-4fac-9a7b-40ea353726e2' AND transaction_type = 'reserve'"))
        if res.fetchone():
            print("Reservation already exists!")
            return
            
        # Get admin user
        res = await conn.execute(text("SELECT id FROM users WHERE role='admin' LIMIT 1"))
        user_id = res.fetchone()[0]
        
        # Insert reservation transaction
        tx_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        
        await conn.execute(text("""
            INSERT INTO inventory_transactions 
            (id, tenant_id, material_id, transaction_type, quantity, reference_type, reference_id, created_at, updated_at, created_by, is_deleted)
            VALUES (:id, :tenant, :mat, 'reserve', 1.0, 'sales_order_line', :ref, :now, :now, :user, false)
        """), {
            "id": tx_id,
            "tenant": tenant_id,
            "mat": material_id,
            "ref": 'c7c8d198-17b8-4fac-9a7b-40ea353726e2',
            "now": now,
            "user": user_id
        })
        
        # Also need to increment materials.reserved_stock
        await conn.execute(text("""
            UPDATE materials SET reserved_stock = reserved_stock + 1.0 WHERE id = :mat
        """), {"mat": material_id})
        
        print("Successfully inserted missing reservation!")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
