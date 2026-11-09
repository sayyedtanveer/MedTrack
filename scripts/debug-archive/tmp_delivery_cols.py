import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/medtrack")
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='delivery_orders' "
            "ORDER BY ordinal_position"
        ))
        cols = [row[0] for row in r]
        print("DB columns:", cols)

asyncio.run(main())
