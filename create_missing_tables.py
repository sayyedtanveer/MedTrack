import asyncio
from backend.app.infrastructure.container import Container
from backend.app.config import settings
from backend.app.infrastructure.persistence.database import Base
# ensure all models are imported
from backend.app.infrastructure.persistence.models import *

async def create_tables():
    container = Container.create(settings)
    async with container.db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Missing tables created successfully.")

if __name__ == "__main__":
    asyncio.run(create_tables())
