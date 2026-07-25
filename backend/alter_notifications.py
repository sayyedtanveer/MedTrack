import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv('c:/Users/sayye/source/repos/MedTrack/backend/.env')

async def main():
    # Use postgres:postgres for local dev
    db_url = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/medtrack')
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN deep_link VARCHAR(500)"))
            print("Added deep_link column")
        except Exception as e:
            print("deep_link:", str(e))
            
        try:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN target_role VARCHAR(50)"))
            print("Added target_role column")
        except Exception as e:
            print("target_role:", str(e))

asyncio.run(main())
