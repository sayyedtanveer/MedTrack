"""One-time script: normalize material_type values in the DB."""
import asyncio
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


def read_db_url() -> str:
    env_file = Path(__file__).parent / ".env"
    for line in env_file.read_text().splitlines():
        for key in ("ASYNC_DATABASE_URL", "DATABASE_URL"):
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DATABASE_URL not found in .env")


async def main():
    db_url = read_db_url()
    # Convert sync postgres:// → asyncpg driver if needed
    if db_url.startswith("postgresql://") and "asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        # Show current distribution
        result = await conn.execute(
            text("SELECT material_type, count(*) FROM materials GROUP BY material_type ORDER BY material_type")
        )
        rows = result.fetchall()
        print("BEFORE normalization:")
        for r in rows:
            print(f"  {r[0]!r}: {r[1]}")

        # Normalize 'finished' variants
        r1 = await conn.execute(text("""
            UPDATE materials
            SET material_type = 'finished'
            WHERE lower(trim(material_type)) IN (
                'finished', 'finished_good', 'finished_goods',
                'fg', 'finishedgood', 'finishedgoods'
            )
              AND material_type != 'finished'
        """))
        print(f"Updated to 'finished': {r1.rowcount} rows")

        # Normalize 'raw' variants
        r2 = await conn.execute(text("""
            UPDATE materials
            SET material_type = 'raw'
            WHERE lower(trim(material_type)) IN (
                'raw', 'raw_material', 'rawmaterial', 'rm'
            )
              AND material_type != 'raw'
        """))
        print(f"Updated to 'raw': {r2.rowcount} rows")

        # Show after
        result2 = await conn.execute(
            text("SELECT material_type, count(*) FROM materials GROUP BY material_type ORDER BY material_type")
        )
        rows2 = result2.fetchall()
        print("AFTER normalization:")
        for r in rows2:
            print(f"  {r[0]!r}: {r[1]}")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
