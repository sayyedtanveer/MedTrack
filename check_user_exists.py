import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

async def check_user():
    engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
    async with engine.begin() as conn:
        # Check if user exists with exact tenant_id
        result = await conn.execute(sa.text("""
            SELECT id, email, tenant_id, is_active, is_deleted, role, hashed_password
            FROM users 
            WHERE email = :email AND tenant_id = :tenant_id
        """), {
            'email': 'test_supplier@synapse-erp.com',
            'tenant_id': '6e3be467-7ed3-4503-a709-d6c1fce9b1a5'
        })
        row = result.fetchone()
        
        if row:
            user_id, email, tenant_id, is_active, is_deleted, role, pwd_hash = row
            print(f"✓ User found:")
            print(f"  Email: {email}")
            print(f"  Tenant ID: {tenant_id}")
            print(f"  Active: {is_active}")
            print(f"  Deleted: {is_deleted}")
            print(f"  Role: {role}")
            print(f"  Password hash: {pwd_hash[:20]}...")
        else:
            print("✗ User NOT found with that tenant_id")
            
            # Try searching across all tenants
            result = await conn.execute(sa.text("""
                SELECT id, email, tenant_id, is_active, is_deleted
                FROM users 
                WHERE email = :email
            """), {'email': 'test_supplier@synapse-erp.com'})
            all_rows = result.fetchall()
            
            if all_rows:
                print(f"\nFound {len(all_rows)} user(s) with this email in OTHER tenants:")
                for row in all_rows:
                    print(f"  Tenant: {row[2]}")
            else:
                print("\nUser does not exist in ANY tenant.")
    
    await engine.dispose()

asyncio.run(check_user())
