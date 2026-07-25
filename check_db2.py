import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import get_settings

async def main():
    engine = create_async_engine(get_settings().async_database_url)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT id, transaction_type, reference_type, reference_id, quantity, created_at FROM inventory_transactions ORDER BY created_at DESC LIMIT 10"))
        rows = res.fetchall()
        print("Recent Inventory Transactions:")
        for row in rows:
            print(row)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
