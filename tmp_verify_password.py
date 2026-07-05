import asyncio
from backend.app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher

async def main():
    hasher = BcryptPasswordHasher()
    engine = create_async_engine(settings.async_database_url)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT hashed_password FROM users WHERE email = 'sayyedtanveer1410@gmail.com' AND role = 'admin' LIMIT 1"))
        row = result.fetchone()
        hashed = row[0]
        print('HASH', hashed)
        print('VERIFY_SAME', hasher.verify('same', hashed))
        print('VERIFY_E2E', hasher.verify('E2EAdmin@1234', hashed))
    await engine.dispose()

asyncio.run(main())
