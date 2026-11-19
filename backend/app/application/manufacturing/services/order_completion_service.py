"""Complete finished production together for one sales order."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.commands.work_order_commands import CompleteWorkOrderCommand
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class OrderCompletionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def work_orders(
        self, tenant_id: UUID, sales_order_id: UUID, *, lock: bool = False,
    ) -> list[WorkOrderModel]:
        order_query = select(SalesOrderModel).where(
            SalesOrderModel.id == sales_order_id,
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
        )
        if lock:
            order_query = order_query.with_for_update()
        order = (await self.session.execute(order_query)).scalar_one_or_none()
        if order is None:
            raise ValueError("Sales order not found")
        if lock and order.status == "CANCELLED":
            raise ValueError("Cannot complete production for a cancelled sales order")
        query = select(WorkOrderModel).where(
            WorkOrderModel.sales_order_id == sales_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        ).order_by(WorkOrderModel.id)
        if lock:
            query = query.with_for_update()
        return list((await self.session.execute(query)).scalars().all())

    async def complete_ready(
        self, tenant_id: UUID, sales_order_id: UUID, uow: SQLAlchemyUnitOfWork,
    ) -> list[WorkOrderModel]:
        work_orders = await self.work_orders(tenant_id, sales_order_id, lock=True)
        handler = WorkOrderHandler(self.session).with_uow(uow)
        for work_order in work_orders:
            if work_order.status == "FG_RECEIVED":
                await handler.handle_complete(CompleteWorkOrderCommand(
                    tenant_id=tenant_id, work_order_id=work_order.id,
                ))
        await uow.commit()
        return work_orders
