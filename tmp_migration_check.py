import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/medtrack")
    async with engine.connect() as conn:
        # Check alembic_version table
        r = await conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        versions = [row[0] for row in r]
        print("Applied migrations:", versions)

        # Check if p1_op_wf_states is applied
        print("\np1_op_wf_states applied:", "p1_op_wf_states" in versions)
        print("p2_inv_reservation applied:", "p2_inv_reservation" in versions)

        # Check which tables related to reservations exist
        r2 = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name IN "
            "('inventory_reservations', 'material_shortages', 'work_orders') "
            "ORDER BY table_name"
        ))
        print("\nRelevant tables:", [row[0] for row in r2])

asyncio.run(check())
