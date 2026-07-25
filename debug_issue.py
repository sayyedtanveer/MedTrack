import asyncio
import sys
import uuid
import traceback
from decimal import Decimal

sys.path.append('c:\\Users\\sayye\\source\\repos\\MedTrack')

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
SessionLocal = async_sessionmaker(engine)

async def main():
    async with SessionLocal() as session:
        inv_svc = InventoryService(session)
        try:
            # wo: 5faa5b8c-025c-4637-84e7-0c6a07d57c7f
            # material: e2c1deee-51be-4698-8c4c-20aa0d7b027d
            # tenant is missing, but maybe we can just query the WO to get the tenant ID
            from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
            from sqlalchemy import select
            
            result = await session.execute(select(WorkOrderModel).where(WorkOrderModel.id == uuid.UUID('5faa5b8c-025c-4637-84e7-0c6a07d57c7f')))
            wo = result.scalar_one_or_none()
            if not wo:
                print("WO not found")
                return
            
            await inv_svc.issue_material_for_wo(
                tenant_id=wo.tenant_id,
                work_order_id=wo.id,
                material_id=uuid.UUID('e2c1deee-51be-4698-8c4c-20aa0d7b027d'),
                quantity=Decimal('2'),
                unit_id=uuid.UUID('533498de-dc4d-4842-840c-43ddc8206c9a'),
                created_by=wo.created_by,
                transition_wo_status=True
            )
            await session.commit()
            print("Successfully issued!")
        except Exception as e:
            traceback.print_exc()

asyncio.run(main())
