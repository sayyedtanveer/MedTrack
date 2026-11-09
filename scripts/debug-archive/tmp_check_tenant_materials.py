import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from pathlib import Path

TENANT_ID = "52323f77-709b-4cb8-818e-c1ad16262541"

def read_db_url():
    for line in Path(".env").read_text().splitlines():
        for key in ("ASYNC_DATABASE_URL", "DATABASE_URL"):
            if line.startswith(key + "="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if "asyncpg" not in url:
                    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
                    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
                return url

async def main():
    engine = create_async_engine(read_db_url())
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT code, name, material_type, is_active, is_deleted "
            "FROM materials "
            "WHERE tenant_id = :tid "
            "ORDER BY material_type, code"
        ), {"tid": TENANT_ID})
        rows = r.fetchall()
        print(f"All materials for tenant {TENANT_ID} ({len(rows)} total):")
        for row in rows:
            print(f"  [{row[2]}] {row[0]} — {row[1]} (active={row[3]}, deleted={row[4]})")
    await engine.dispose()

asyncio.run(main())
