import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/medtrack")
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name IN ('inventory_reservations','materials') "
            "ORDER BY table_name"
        ))
        tables = [row[0] for row in r]
        print("Tables found:", tables)

        # Check inventory_reservations columns if it exists
        if "inventory_reservations" in tables:
            r2 = await conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name='inventory_reservations' ORDER BY ordinal_position"
            ))
            print("inventory_reservations columns:")
            for row in r2:
                print(" ", row[0], row[1])

asyncio.run(check())
