from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from backend.app.application.delivery.delivery_service import DeliveryService
from backend.app.application.manufacturing.services.order_completion_service import OrderCompletionService
from backend.app.infrastructure.persistence.models.delivery_model import DeliveryLineModel, DeliveryOrderModel
from backend.app.infrastructure.persistence.models.sales_models import ClientModel, SalesOrderLineModel, SalesOrderModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.routes.delivery_dashboard import get_dispatch_queue


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as connection:
        for model in (ClientModel, SalesOrderModel, SalesOrderLineModel, WorkOrderModel,
                      DeliveryOrderModel, DeliveryLineModel):
            await connection.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        yield db
    await engine.dispose()


async def seed_order(session):
    tenant = uuid4()
    order = SalesOrderModel(id=uuid4(), tenant_id=tenant, order_number='TEST-PARTIAL',
                            client_id=uuid4(), created_by=str(uuid4()), order_date='2026-01-01',
                            delivery_date='2026-01-02', status='PRODUCTION')
    lines = [SalesOrderLineModel(
        id=uuid4(), sales_order_id=order.id, product_id=uuid4(), product_type='variant',
        uom_id=uuid4(), quantity=1, unit_price=10, allocated_quantity=allocated,
    ) for allocated in (1, 0)]
    session.add_all([order, *lines])
    await session.commit()
    return tenant, order, lines


@pytest.mark.asyncio
async def test_partial_order_enters_queue_and_returns_for_remaining_product(session):
    tenant, order, lines = await seed_order(session)
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        container=SimpleNamespace(session_factory=factory),
    )))
    queue = await get_dispatch_queue(request, tenant)
    assert [item['id'] for item in queue] == [str(order.id)]
    assert queue[0]['ready_product_count'] == 1
    assert await get_dispatch_queue(request, uuid4()) == []
    lines[0].dispatched_quantity = 1
    await session.commit()
    assert await get_dispatch_queue(request, tenant) == []
    lines[1].allocated_quantity = 1
    await session.commit()
    assert len(await get_dispatch_queue(request, tenant)) == 1
    order.is_deleted = True
    await session.commit()
    assert await get_dispatch_queue(request, tenant) == []


@pytest.mark.asyncio
async def test_complete_ready_is_repeatable_and_preserves_pending_production(session):
    tenant, order, lines = await seed_order(session)
    work_orders = [WorkOrderModel(
        id=uuid4(), tenant_id=tenant, wo_number=f'TEST-WO-{index}',
        sales_order_id=order.id, sales_order_line_id=line.id, product_id=line.product_id,
        bom_id=uuid4(), planned_quantity=1, produced_quantity=1 if index == 0 else 0,
        status='FG_RECEIVED' if index == 0 else 'IN_PRODUCTION',
        priority='NORMAL', start_date=date(2026, 1, 1), due_date=date(2026, 1, 2),
        created_by=uuid4(),
    ) for index, line in enumerate(lines)]
    session.add_all(work_orders)
    await session.commit()
    dispatcher = SimpleNamespace(dispatch=AsyncMock())
    uow = SQLAlchemyUnitOfWork(session, dispatcher)
    service = OrderCompletionService(session)
    await service.complete_ready(tenant, order.id, uow)
    assert work_orders[0].status == 'COMPLETED'
    assert work_orders[1].status == 'IN_PRODUCTION'
    await service.complete_ready(tenant, order.id, uow)
    dispatcher.dispatch.assert_awaited_once()
    with pytest.raises(ValueError, match='not found'):
        await service.complete_ready(uuid4(), order.id, uow)


@pytest.mark.asyncio
@pytest.mark.parametrize('deliver_first_early', [True, False])
async def test_partial_delivery_waits_for_remaining_products_before_invoice(session, monkeypatch, deliver_first_early):
    tenant, order, lines = await seed_order(session)
    from backend.app.application.delivery import delivery_service as module
    monkeypatch.setattr(module.SalesInventoryIntegrationService, 'fulfill_reservation', AsyncMock())
    invoice = AsyncMock()
    monkeypatch.setattr(module.WorkflowOrchestrationService, 'on_order_delivered', invoice)
    service = DeliveryService(session)

    async def delivery_for(line, number):
        delivery = DeliveryOrderModel(id=uuid4(), tenant_id=tenant, delivery_number=number,
                                       sales_order_id=order.id, created_by=uuid4(), status='DRAFT')
        delivery.lines = [DeliveryLineModel(id=uuid4(), tenant_id=tenant,
            delivery_order_id=delivery.id, sales_order_line_id=line.id,
            variant_id=line.product_id, quantity=1)]
        session.add(delivery)
        await session.commit()
        return delivery

    first = await delivery_for(lines[0], 'TEST-DO-1')
    await service.ship(tenant_id=tenant, delivery_id=first.id, shipped_by=uuid4())
    assert order.status == 'PRODUCTION'
    if deliver_first_early:
        await service.deliver(tenant_id=tenant, delivery_id=first.id, delivered_by=uuid4())
    invoice.assert_not_awaited()
    lines[1].allocated_quantity = 1
    second = await delivery_for(lines[1], 'TEST-DO-2')
    await service.ship(tenant_id=tenant, delivery_id=second.id, shipped_by=uuid4())
    assert order.status == 'SHIPPED'
    if not deliver_first_early:
        await service.deliver(tenant_id=tenant, delivery_id=first.id, delivered_by=uuid4())
        invoice.assert_not_awaited()
    await service.deliver(tenant_id=tenant, delivery_id=second.id, delivered_by=uuid4())
    invoice.assert_awaited_once()
