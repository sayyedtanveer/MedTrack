import asyncio
from backend.app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher

async def main():
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash('same')
    engine = create_async_engine(settings.async_database_url)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET hashed_password = :hashed WHERE email = :email"),
            {'hashed': hashed, 'email': 'sayyedtanveer1410@gmail.com'}
        )
    await engine.dispose()
    print('UPDATED')

asyncio.run(main())
