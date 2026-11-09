import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import get_settings

async def main():
    engine = create_async_engine(get_settings().async_database_url)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT id, sales_order_id, sales_order_line_id FROM work_orders WHERE id = '5faa5b8c-025c-4637-84e7-0c6a07d57c7f'"))
        rows = res.fetchall()
        print("Work Order linkage:")
        for row in rows:
            print(row)
            
        print("\nSales Order Lines:")
        res = await conn.execute(text("SELECT id, quantity, allocated_quantity, backorder_quantity, status FROM sales_order_lines"))
        for row in res.fetchall():
            print(row)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
