import asyncio
import uuid
from backend.app.infrastructure.container import Container
from backend.app.config import settings
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler, CompleteWorkOrderCommand
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from sqlalchemy import select
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel

async def main():
    container = Container.create(settings)
    
    async with container.session_factory() as session:
        tenant_id = (await session.execute(select(TenantModel.id).limit(1))).scalar_one_or_none()
        wo_id = uuid.UUID("5faa5b8c-025c-4637-84e7-0c6a07d57c7f")
        
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        
        try:
            print(f"Calling handle_complete with tenant_id type: {type(tenant_id)}")
            cmd = CompleteWorkOrderCommand(tenant_id=tenant_id, work_order_id=wo_id)
            await handler.handle_complete(cmd)
            await uow.commit()
            print("Successfully completed work order!")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
