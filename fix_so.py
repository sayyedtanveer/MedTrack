import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel

async def fix():
    engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        stmt = update(SalesOrderModel).where(SalesOrderModel.order_number == 'SO-20260725-001').values(status='COMPLETED')
        await session.execute(stmt)
        await session.commit()
    print('Fixed!')

asyncio.run(fix())
