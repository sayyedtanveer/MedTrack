import asyncio
from backend.app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select, text
from backend.app.infrastructure.persistence.models.user_model import UserModel

async def main():
    engine = create_async_engine(settings.async_database_url)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, email, tenant_id, is_active, role, hashed_password FROM users WHERE email IN ('admin.e2e@medtrack-demo.com', 'sayyedtanveer1410@gmail.com') ORDER BY email"))
        for row in result.fetchall():
            print('EMAIL', row[1])
            print('TENANT', row[2])
            print('ACTIVE', row[3])
            print('ROLE', row[4])
            print('HASH', row[5][:80])
    await engine.dispose()

asyncio.run(main())
