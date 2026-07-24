"""
Generate a raw SQL script from all pending Alembic migration upgrade() functions.
Skips already-applied revisions.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

APPLIED = {
    "add_default_price_list_to_clients",
    "add_notification_retention",
    "normalize_material_type_001",
}

async def get_applied():
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/medtrack")
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT version_num FROM alembic_version"))
        return {row[0] for row in r}

applied = asyncio.run(get_applied())
print("Already applied:", sorted(applied))
