import asyncio
import uuid
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Mock the container and imports to run just the handler
from backend.app.infrastructure.persistence.database import create_engine, create_session_factory
from backend.app.domain.sales.repositories.sales_order_repository import SalesOrderRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.application.sales.commands import SubmitSalesOrderForApprovalCommand
from backend.app.application.sales.command_handlers import SubmitSalesOrderForApprovalCommandHandler
from backend.app.interfaces.api.sales.routes import _resolve_order_approver_id, _notify_sales_order_submitted
import os

class DummyEventDispatcher:
    async def dispatch(self, event):
        pass

class DummyEmailService:
    pass

class DummyConnectionManager:
    async def send_to_user(self, *args, **kwargs):
        pass

class DummyContainer:
    def __init__(self):
        self.event_dispatcher = DummyEventDispatcher()
        self.email_service = DummyEmailService()
        self.connection_manager = DummyConnectionManager()

async def test_submit():
    database_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:123@localhost:5432/medtrack")
    engine = create_engine(database_url)
    async_session = create_session_factory(engine)
    
    order_id = uuid.UUID("b0e1d83e-fd9b-4b77-b53c-04568725f32b")
    # Need to figure out the tenant_id, just grab it from the order
    async with async_session() as session:
        from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
        from sqlalchemy import select
        
        result = await session.execute(select(SalesOrderModel).where(SalesOrderModel.id == order_id))
        order_model = result.scalar_one_or_none()
        if not order_model:
            print(f"Order {order_id} not found!")
            return
            
        tenant_id = order_model.tenant_id
        print(f"Found order with tenant {tenant_id}, status {order_model.status}")

        
        if order_model.status != "DRAFT":
            print("Order is not DRAFT. Resetting to DRAFT...")
            order_model.status = "DRAFT"
            await session.commit()
            
    # Now run the logic exactly like the route
    container = DummyContainer()
    async with async_session() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = SubmitSalesOrderForApprovalCommandHandler(order_repo, uow)
        
        print("Resolving approver...")
        approver_id = await _resolve_order_approver_id(session, tenant_id)
        print(f"Approver resolved: {approver_id}")
        
        print("Handling command...")
        user_id = uuid.uuid4() # dummy
        command = SubmitSalesOrderForApprovalCommand(
            tenant_id=tenant_id,
            sales_order_id=order_id,
            submitted_by=str(user_id),
            approver_id=approver_id,
            notes=None,
        )
        await handler.handle(command)
        print("Handler succeeded.")
        
        print("Fetching order to notify...")
        order = await order_repo.get_by_id(order_id, tenant_id)
        if order:
            print("Notifying...")
            await _notify_sales_order_submitted(session, container, tenant_id, order)
            print("Notification succeeded.")

if __name__ == "__main__":
    asyncio.run(test_submit())
