import asyncio
import uuid
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from datetime import date, datetime, timezone

async def add_test_data():
    engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
    async with engine.begin() as conn:
        supplier_id = "8f15d553-365d-430e-8298-c451189a4045"
        tenant_id = "6e3be467-7ed3-4503-a709-d6c1fce9b1a5"
        
        # Check if supplier exists
        result = await conn.execute(sa.text("""
            SELECT id FROM suppliers WHERE id = :id
        """), {"id": supplier_id})
        if not result.fetchone():
            print("✗ Supplier not found")
            return
        
        # Get or create a material
        mat_result = await conn.execute(sa.text("""
            SELECT id FROM materials WHERE tenant_id = :tenant_id LIMIT 1
        """), {"tenant_id": tenant_id})
        mat = mat_result.fetchone()
        
        if not mat:
            print("No materials found. Creating one...")
            material_id = str(uuid.uuid4())
            await conn.execute(sa.text("""
                INSERT INTO materials (id, tenant_id, code, name, is_active, created_at, updated_at)
                VALUES (:id, :tenant_id, 'MAT-001', 'Test Material', true, NOW(), NOW())
            """), {"id": material_id, "tenant_id": tenant_id})
        else:
            material_id = str(mat[0])
        
        # Create a test PO for this supplier
        po_id = str(uuid.uuid4())
        po_number = f"PO-{str(uuid.uuid4())[:8].upper()}"
        
        await conn.execute(sa.text("""
            INSERT INTO purchase_orders 
            (id, tenant_id, po_number, supplier_id, order_date, expected_delivery, status, total_amount, is_active, is_deleted, created_at, updated_at)
            VALUES (:id, :tenant_id, :po_number, :supplier_id, :order_date, :expected_delivery, 'sent', 1000.00, true, false, NOW(), NOW())
        """), {
            "id": po_id,
            "tenant_id": tenant_id,
            "po_number": po_number,
            "supplier_id": supplier_id,
            "order_date": date.today(),
            "expected_delivery": date.today()
        })
        
        # Create a PO line
        line_id = str(uuid.uuid4())
        await conn.execute(sa.text("""
            INSERT INTO purchase_order_lines
            (id, tenant_id, purchase_order_id, material_id, quantity, received_quantity, unit_price, line_total, is_deleted, created_at, updated_at)
            VALUES (:id, :tenant_id, :po_id, :material_id, 100, 0, 10.00, 1000.00, false, NOW(), NOW())
        """), {
            "id": line_id,
            "tenant_id": tenant_id,
            "po_id": po_id,
            "material_id": material_id
        })
        
        print(f"✓ Test data created:")
        print(f"  PO: {po_number} (status: sent)")
        print(f"  Material: {material_id}")
        print(f"\nVisit http://localhost:3000/supplier-portal to see the PO")
    
    await engine.dispose()

asyncio.run(add_test_data())
