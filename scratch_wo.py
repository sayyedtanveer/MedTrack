import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('backend/app'))
sys.path.insert(0, os.path.abspath('backend'))

from app.infrastructure.persistence.database import create_engine, create_session_factory
from app.core.config import settings
from sqlalchemy import text

async def run():
    engine = create_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        res = await session.execute(text("SELECT status, COUNT(*) FROM work_orders GROUP BY status"))
        print("WORK ORDERS:", res.fetchall())
        
if __name__ == '__main__':
    asyncio.run(run())
