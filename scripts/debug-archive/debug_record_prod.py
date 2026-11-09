import asyncio
import uuid
import sys
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.infrastructure.container import Container
from backend.app.config import settings
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler, RecordProductionCommand
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel

async def main():
    container = Container.create(settings)
    
    # We need to get a session
    async with container.session_factory() as session:
        # Find the tenant and user for testing
        tenant_id = (await session.execute(select(TenantModel.id).limit(1))).scalar_one_or_none()
        user_id = (await session.execute(select(UserModel.id).where(UserModel.tenant_id == tenant_id).limit(1))).scalar_one_or_none()
        
        if not tenant_id or not user_id:
            print("No tenant or user found.")
            return
            
        wo_id = uuid.UUID("5faa5b8c-025c-4637-84e7-0c6a07d57c7f")
        
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        
        try:
            cmd = RecordProductionCommand(
                tenant_id=tenant_id,
                work_order_id=wo_id,
                recorded_by=user_id,
                produced_quantity=1.000,
                scrap_quantity=0,
                notes="Testing record production"
            )
            print(f"Calling handle_record_production...")
            await handler.handle_record_production(cmd)
            await uow.commit()
            print("Successfully recorded production!")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
