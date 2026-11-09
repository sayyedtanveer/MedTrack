import asyncio
import uuid
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from datetime import date

async def add_test_data():
    """Add test PO without using is_active column that doesn't exist"""
    engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
    async with engine.begin() as conn:
        supplier_id = "8f15d553-365d-430e-8298-c451189a4045"
        tenant_id = "6e3be467-7ed3-4503-a709-d6c1fce9b1a5"
        
        # Get first material
        mat_result = await conn.execute(sa.text("""
            SELECT id FROM materials WHERE tenant_id = :tenant_id LIMIT 1
        """), {"tenant_id": tenant_id})
        mat = mat_result.fetchone()
        
        if not mat:
            print("No materials. Creating one...")
            material_id = str(uuid.uuid4())
            await conn.execute(sa.text("""
                INSERT INTO materials (id, tenant_id, code, name, created_at, updated_at)
                VALUES (:id, :tenant_id, 'MAT-001', 'Test Material', NOW(), NOW())
            """), {"id": material_id, "tenant_id": tenant_id})
        else:
            material_id = str(mat[0])
        
        # Find a user to use as created_by
        user_result = await conn.execute(sa.text("""
            SELECT id FROM users WHERE tenant_id = :tenant_id LIMIT 1
        """), {"tenant_id": tenant_id})
        user_row = user_result.fetchone()
        if not user_row:
            raise SystemExit("No user found for tenant to set created_by")
        created_by = str(user_row[0])

        # Create PO without is_active
        po_id = str(uuid.uuid4())
        po_number = f"PO-TEST-001"
        
        await conn.execute(sa.text("""
            INSERT INTO purchase_orders 
            (id, tenant_id, po_number, supplier_id, order_date, expected_delivery, status, total_amount, is_deleted, created_by, created_at, updated_at)
            VALUES (:id, :tenant_id, :po_number, :supplier_id, :order_date, :expected_delivery, 'sent', 1000.00, false, :created_by, NOW(), NOW())
        """), {
            "id": po_id,
            "tenant_id": tenant_id,
            "po_number": po_number,
            "supplier_id": supplier_id,
            "order_date": date.today(),
            "expected_delivery": date.today(),
            "created_by": created_by,
        })
        
        # Create PO line without is_deleted, line_total
        line_id = str(uuid.uuid4())
        await conn.execute(sa.text("""
            INSERT INTO purchase_order_lines
            (id, tenant_id, purchase_order_id, material_id, quantity, received_quantity, unit_price, created_at, updated_at)
            VALUES (:id, :tenant_id, :po_id, :material_id, 100, 0, 10.00, NOW(), NOW())
        """), {
            "id": line_id,
            "tenant_id": tenant_id,
            "po_id": po_id,
            "material_id": material_id
        })
        
        print(f"✓ Test PO created: {po_number}")
        print(f"  Status: sent (ready to acknowledge)")
        print(f"  Refresh http://localhost:3000/supplier-portal to see it")
    
    await engine.dispose()

asyncio.run(add_test_data())
