"""Check actual DB state for all relevant tables."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

URL = "postgresql+asyncpg://postgres:123@localhost:5432/medtrack"

async def check():
    engine = create_async_engine(URL)
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        print("DB alembic versions:", [row[0] for row in r.fetchall()])

        # Check document_associations columns
        r2 = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'document_associations' ORDER BY ordinal_position"
        ))
        print("document_associations columns:", [row[0] for row in r2.fetchall()])

        # Check subcontract tables
        r3 = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name LIKE 'subcontract%' ORDER BY table_name"
        ))
        print("subcontract tables:", [row[0] for row in r3.fetchall()])

        # Check work_order related tables
        r4 = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name LIKE 'work_order%' ORDER BY table_name"
        ))
        print("work_order tables:", [row[0] for row in r4.fetchall()])

        # Check if document_associations even exists
        r5 = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('document_associations','technical_documents','document_revisions','file_attachments','documents')"
        ))
        print("document tables:", [row[0] for row in r5.fetchall()])

    await engine.dispose()

asyncio.run(check())
