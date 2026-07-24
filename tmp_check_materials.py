"""Debug: check what the materials API returns for finished type."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from pathlib import Path


def read_db_url():
    for line in Path(".env").read_text().splitlines():
        for key in ("ASYNC_DATABASE_URL", "DATABASE_URL"):
            if line.startswith(key + "="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if "asyncpg" not in url:
                    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
                    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
                return url
    raise RuntimeError("DATABASE_URL not found")


async def main():
    engine = create_async_engine(read_db_url())
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT id, code, name, material_type, is_active, is_deleted "
            "FROM materials WHERE material_type = 'finished' LIMIT 15"
        ))
        rows = r.fetchall()
        print(f"Finished materials ({len(rows)} shown):")
        for row in rows:
            print(f"  code={row[1]!r}  name={row[2]!r}  type={row[3]!r}  active={row[4]}  deleted={row[5]}")

        # Also check FG-MET-0001 specifically
        r2 = await conn.execute(text(
            "SELECT id, code, name, material_type, is_active, is_deleted "
            "FROM materials WHERE code LIKE 'FG-MET%' LIMIT 5"
        ))
        rows2 = r2.fetchall()
        print(f"\nFG-MET materials:")
        for row in rows2:
            print(f"  code={row[1]!r}  name={row[2]!r}  type={row[3]!r}  active={row[4]}  deleted={row[5]}")

    await engine.dispose()


asyncio.run(main())
