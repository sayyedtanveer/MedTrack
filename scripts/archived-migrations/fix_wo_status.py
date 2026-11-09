import asyncio
import sys
sys.path.append('c:\\Users\\sayye\\source\\repos\\MedTrack')

from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/medtrack')
SessionLocal = async_sessionmaker(engine)

async def main():
    async with SessionLocal() as session:
        result = await session.execute(select(WorkOrderModel).where(WorkOrderModel.wo_number == 'WO-20260725-0001'))
        wo = result.scalar_one_or_none()
        if wo:
            wo.status = 'IN_PRODUCTION'
            await session.commit()
            print('Fixed WO status to IN_PRODUCTION')
        else:
            print('WO not found')

asyncio.run(main())
