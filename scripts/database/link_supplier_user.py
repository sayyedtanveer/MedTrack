"""
Quick script to link a supplier user account to a supplier.
This ensures their JWT includes the 'sid' (supplier_id) claim.
"""
import asyncio
import sqlalchemy as sa
import uuid
from sqlalchemy.ext.asyncio import create_async_engine

async def link_supplier_user():
    engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
    async with engine.begin() as conn:
        # Find the user 'supperali' or similar
        result = await conn.execute(sa.text("""
            SELECT id, email, tenant_id FROM users 
            WHERE email ILIKE :email_pattern 
            LIMIT 1
        """), {"email_pattern": "%supperali%"})
        user_row = result.fetchone()
        
        if not user_row:
            print("No user matching 'supperali' found. Trying to find any supplier-role user...")
            result = await conn.execute(sa.text("""
                SELECT id, email, tenant_id FROM users 
                WHERE role = 'supplier' AND supplier_id IS NULL
                LIMIT 1
            """))
            user_row = result.fetchone()
        
        if not user_row:
            print("No unlinked supplier user found. Creating one...")
            # Create a test supplier first
            tenant_result = await conn.execute(sa.text("SELECT id FROM tenants LIMIT 1"))
            tenant_row = tenant_result.fetchone()
            if not tenant_row:
                print("No tenant found. Cannot proceed.")
                return
            tenant_id = tenant_row[0]
            
            supplier_id = str(uuid.uuid4())
            await conn.execute(sa.text("""
                INSERT INTO suppliers (id, tenant_id, name, code, is_active, created_at, updated_at)
                VALUES (:id, :tenant_id, 'Test Supplier', 'TST-SUP-001', true, NOW(), NOW())
            """), {"id": supplier_id, "tenant_id": tenant_id})
            
            user_id = str(uuid.uuid4())
            await conn.execute(sa.text("""
                INSERT INTO users (id, email, hashed_password, first_name, last_name, role, is_active, tenant_id, supplier_id, created_at, updated_at)
                VALUES (:id, :email, :pwd, 'Test', 'Supplier', 'supplier', true, :tenant_id, :supplier_id, NOW(), NOW())
            """), {
                "id": user_id,
                "email": "testsupplier@test.com",
                "pwd": "$2b$12$dummyhash",  # dummy
                "tenant_id": tenant_id,
                "supplier_id": supplier_id
            })
            print(f"✓ Created user 'testsupplier@test.com' linked to supplier {supplier_id}")
            return
        
        user_id, user_email, tenant_id = user_row
        
        # Check if user already has a supplier link
        existing_link = await conn.execute(sa.text("""
            SELECT supplier_id FROM users WHERE id = :user_id
        """), {"user_id": user_id})
        existing = existing_link.fetchone()
        if existing and existing[0]:
            print(f"✓ User {user_email} already linked to supplier {existing[0]}")
            return
        
        # Get or create a supplier
        supplier_result = await conn.execute(sa.text("""
            SELECT id FROM suppliers 
            WHERE tenant_id = :tenant_id AND is_active = true
            LIMIT 1
        """), {"tenant_id": tenant_id})
        supplier_row = supplier_result.fetchone()
        
        if not supplier_row:
            print("Creating a default supplier for tenant...")
            supplier_id = str(uuid.uuid4())
            await conn.execute(sa.text("""
                INSERT INTO suppliers (id, tenant_id, name, code, is_active, created_at, updated_at)
                VALUES (:id, :tenant_id, 'Default Test Supplier', 'DEFAULT-001', true, NOW(), NOW())
            """), {"id": supplier_id, "tenant_id": tenant_id})
        else:
            supplier_id = supplier_row[0]
        
        # Link user to supplier
        await conn.execute(sa.text("""
            UPDATE users SET supplier_id = :supplier_id, updated_at = NOW()
            WHERE id = :user_id
        """), {"supplier_id": supplier_id, "user_id": user_id})
        
        print(f"✓ Linked user '{user_email}' (ID: {user_id}) to supplier {supplier_id}")
        print(f"  Next login will include 'sid' claim in JWT.")
        print(f"  Try: http://localhost:3000/supplier-portal")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(link_supplier_user())
