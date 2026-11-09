"""Apply document_associations column additions directly via SQL.
This bypasses the broken Alembic multi-head chain issue.
Idempotent - safe to run multiple times.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

URL = "postgresql+asyncpg://postgres:123@localhost:5432/medtrack"

async def apply():
    engine = create_async_engine(URL)
    async with engine.begin() as conn:
        # Check and add work_order_line_id
        r = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='document_associations' AND column_name='work_order_line_id'"
        ))
        if not r.fetchone():
            await conn.execute(text(
                "ALTER TABLE document_associations ADD COLUMN work_order_line_id UUID"
            ))
            print("Added work_order_line_id to document_associations")
        else:
            print("work_order_line_id already exists")

        # Check and add show_on_wo
        r2 = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='document_associations' AND column_name='show_on_wo'"
        ))
        if not r2.fetchone():
            await conn.execute(text(
                "ALTER TABLE document_associations ADD COLUMN show_on_wo BOOLEAN NOT NULL DEFAULT true"
            ))
            print("Added show_on_wo to document_associations")
        else:
            print("show_on_wo already exists")

        # Stamp b3f8e1a2c9d4 in alembic_version so Alembic knows this migration ran
        r3 = await conn.execute(text(
            "SELECT version_num FROM alembic_version WHERE version_num = 'b3f8e1a2c9d4'"
        ))
        if not r3.fetchone():
            await conn.execute(text(
                "INSERT INTO alembic_version (version_num) VALUES ('b3f8e1a2c9d4')"
            ))
            print("Stamped b3f8e1a2c9d4 in alembic_version")
        else:
            print("b3f8e1a2c9d4 already in alembic_version")

    await engine.dispose()
    print("Done.")

asyncio.run(apply())
