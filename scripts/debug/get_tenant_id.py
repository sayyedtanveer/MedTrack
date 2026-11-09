import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

async def get_tenant():
    engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
    async with engine.begin() as conn:
        result = await conn.execute(sa.text('SELECT id, tenant_id, email, supplier_id FROM users WHERE email = :email'), {'email': 'test_supplier@synapse-erp.com'})
        row = result.fetchone()
        if row:
            user_id, tenant_id, email, supplier_id = row
            print(f"Email: {email}")
            print(f"Tenant ID: {tenant_id}")
            print(f"Supplier ID: {supplier_id}")
        else:
            print('User not found')
    await engine.dispose()

asyncio.run(get_tenant())
