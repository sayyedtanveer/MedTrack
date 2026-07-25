import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv('c:/Users/sayye/source/repos/MedTrack/backend/.env')

async def main():
    db_url = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/medtrack')
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'quality_inspections_result_check'"))
        row = res.fetchone()
        print('Constraint definition:', row[0] if row else 'Not found')
        
asyncio.run(main())
