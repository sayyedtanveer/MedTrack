from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.infrastructure.persistence.models.inventory_management_models import StockLedgerModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository
from backend.app.application.inventory.commands.inventory_commands import CreateMaterialCommand
from backend.app.application.inventory.handlers.inventory_handlers import CreateMaterialHandler
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as connection:
        for model in (MaterialModel, LocationModel, StockLevelModel, InventoryTransactionModel, StockLedgerModel):
            await connection.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
    async with async_sessionmaker(engine, expire_on_commit=False, autoflush=False)() as db:
        yield db
    await engine.dispose()


async def seed(session, stock=2000, *, inspection_required=False):
    tenant, actor = uuid4(), uuid4()
    location = LocationModel(id=uuid4(), tenant_id=tenant, name='Warehouse', type='warehouse')
    material = MaterialModel(id=uuid4(), tenant_id=tenant, code='TEST-PLANK', name='Test plank',
                             material_type='raw', current_stock=stock, reserved_stock=20 if stock else 0,
                             base_unit_id=uuid4(), inspection_required=inspection_required)
    session.add_all([material, location])
    await session.commit()
    return tenant, actor, material, location


@pytest.mark.asyncio
async def test_assignment_preserves_total_reservations_and_records_zero_quantity_change(session):
    tenant, actor, material, location = await seed(session)
    service = InventoryService(session)
    assigned = await service.assign_unlocated_stock(tenant_id=tenant, material_id=material.id,
        location_id=location.id, created_by=actor, remarks='Physical stock verified')
    await session.commit()
    assert assigned == 2000
    assert material.current_stock == 2000
    assert material.reserved_stock == 20
    assert await service._sum_all_stock_levels(tenant, material.id) == 2000
    ledger = (await session.execute(select(StockLedgerModel))).scalar_one()
    assert ledger.quantity_change == 0
    assert ledger.running_balance == 2000
    transactions = await TransactionRepository(session).list_by_material(material.id, tenant)
    assert transactions[0].transaction_type.value == 'LOCATION_ASSIGNMENT'
    assert transactions[0].reference_type.value == 'location_reconciliation'
    assert transactions[0].to_location_id == location.id
    assert await service.assign_unlocated_stock(tenant_id=tenant, material_id=material.id,
        location_id=location.id, created_by=actor, remarks='Retry') == 0
    assert await session.scalar(select(func.count()).select_from(InventoryTransactionModel)) == 1


@pytest.mark.asyncio
async def test_assignment_only_fills_missing_balance_and_preserves_quality_status(session):
    tenant, actor, material, location = await seed(session, inspection_required=True)
    session.add(StockLevelModel(id=uuid4(), tenant_id=tenant, material_id=material.id,
                               location_id=location.id, stock_status='quarantine', quantity=500))
    await session.commit()
    assigned = await InventoryService(session).assign_unlocated_stock(
        tenant_id=tenant, material_id=material.id, location_id=location.id,
        created_by=actor, remarks='Locate remaining stock')
    await session.commit()
    assert assigned == 1500
    buckets = (await session.execute(select(StockLevelModel))).scalars().all()
    assert {bucket.stock_status: bucket.quantity for bucket in buckets} == {
        'quarantine': 500, 'pending_inspection': 1500,
    }
    assert material.current_stock == 2000


@pytest.mark.asyncio
@pytest.mark.parametrize('invalid', ['other_tenant', 'inactive', 'deleted', 'subcontractor'])
async def test_assignment_rejects_unusable_locations(session, invalid):
    tenant, actor, material, location = await seed(session)
    if invalid == 'other_tenant':
        location.tenant_id = uuid4()
    elif invalid == 'inactive':
        location.is_active = False
    elif invalid == 'deleted':
        location.is_deleted = True
    else:
        location.type = 'subcontractor'
    await session.commit()
    with pytest.raises(ValueError, match='active internal'):
        await InventoryService(session).assign_unlocated_stock(tenant_id=tenant,
            material_id=material.id, location_id=location.id, created_by=actor, remarks='Test')
    assert material.current_stock == 2000
    assert await session.scalar(select(func.count()).select_from(StockLevelModel)) == 0


@pytest.mark.asyncio
async def test_wrong_tenant_cannot_assign_material_stock(session):
    tenant, actor, material, location = await seed(session)
    with pytest.raises(ValueError, match='not found'):
        await InventoryService(session).assign_unlocated_stock(tenant_id=uuid4(),
            material_id=material.id, location_id=location.id, created_by=actor, remarks='Test')


@pytest.mark.asyncio
async def test_receive_cannot_erase_unlocated_stock_and_adds_normally_after_assignment(session):
    tenant, actor, material, location = await seed(session)
    service = InventoryService(session)
    with pytest.raises(ValueError, match='Assign existing'):
        await service.add_stock(tenant_id=tenant, material_id=material.id,
            quantity=Decimal('100'), unit_id=material.base_unit_id, created_by=actor,
            to_location_id=location.id)
    await service.assign_unlocated_stock(tenant_id=tenant, material_id=material.id,
        location_id=location.id, created_by=actor, remarks='Stock verified')
    await service.add_stock(tenant_id=tenant, material_id=material.id,
        quantity=Decimal('100'), unit_id=material.base_unit_id, created_by=actor,
        to_location_id=location.id)
    await session.commit()
    assert material.current_stock == 2100
    assert await service._sum_all_stock_levels(tenant, material.id) == 2100


@pytest.mark.asyncio
async def test_new_opening_stock_records_quantity_at_location_once(session):
    tenant, actor, material, location = await seed(session, stock=0)
    service = InventoryService(session)
    await service.receive_opening_stock(tenant_id=tenant, material_id=material.id,
        quantity=Decimal('2000'), created_by=actor, location_id=location.id)
    await session.commit()
    assert material.current_stock == 2000
    assert material.location_id == location.id
    assert await service._sum_all_stock_levels(tenant, material.id) == 2000
    assert await session.scalar(select(func.count()).select_from(InventoryTransactionModel)) == 1
    with pytest.raises(ValueError, match='without existing stock'):
        await service.receive_opening_stock(tenant_id=tenant, material_id=material.id,
            quantity=Decimal('2000'), created_by=actor, location_id=location.id)


@pytest.mark.asyncio
async def test_opening_stock_requires_a_physical_storage_location(session):
    tenant, actor, material, location = await seed(session, stock=0)
    location.is_active = False
    await session.commit()
    with pytest.raises(ValueError, match='active internal'):
        await InventoryService(session).receive_opening_stock(
            tenant_id=tenant, material_id=material.id, quantity=Decimal('2000'), created_by=actor)
    assert material.current_stock == 0
    assert await session.scalar(select(func.count()).select_from(InventoryTransactionModel)) == 0


@pytest.mark.asyncio
async def test_assignment_refuses_location_balances_above_total_stock(session):
    tenant, actor, material, location = await seed(session)
    session.add(StockLevelModel(id=uuid4(), tenant_id=tenant, material_id=material.id,
        location_id=location.id, stock_status='available', quantity=2500))
    await session.commit()
    with pytest.raises(ValueError, match='exceed total'):
        await InventoryService(session).assign_unlocated_stock(tenant_id=tenant,
            material_id=material.id, location_id=location.id, created_by=actor, remarks='Test')
    assert material.current_stock == 2000
    assert await session.scalar(select(func.count()).select_from(InventoryTransactionModel)) == 0


@pytest.mark.asyncio
async def test_create_material_entry_point_places_opening_stock_at_selected_location(session):
    tenant, actor, _, location = await seed(session, stock=0)
    handler = CreateMaterialHandler(MaterialRepository(session), SQLAlchemyUnitOfWork(session, None))
    result = await handler.handle(CreateMaterialCommand(
        tenant_id=tenant, created_by=actor, code='TEST-OPENING', name='Opening material',
        material_type='raw', category_id=uuid4(), base_unit_id=uuid4(),
        location_id=location.id, opening_stock=Decimal('2000'),
    ))
    assert result.current_stock == 2000
    assert await InventoryService(session)._sum_all_stock_levels(tenant, result.id) == 2000
    transaction = (await session.execute(select(InventoryTransactionModel).where(
        InventoryTransactionModel.material_id == result.id,
    ))).scalar_one()
    assert transaction.quantity == 2000
    assert transaction.to_location_id == location.id
    assert transaction.reference_type == 'opening_balance'
