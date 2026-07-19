from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.infrastructure.persistence.models.batch_model import BatchModel
from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
    InventoryReservationModel,
)
from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.material_shortage_model import (
    MaterialShortageModel,
)
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderMaterialModel,
    WorkOrderModel,
)


@pytest.mark.asyncio
async def test_wo_issue_and_consume_lifecycle_keeps_partial_issue_open(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    material_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    work_order_id = uuid.uuid4()
    product_id = uuid.uuid4()
    bom_id = uuid.uuid4()

    db_session.add(
        MaterialModel(
            id=material_id,
            tenant_id=test_tenant_id,
            code="RM-LIFE",
            item_code="RM-LIFE",
            name="Lifecycle RM",
            material_type="raw",
            current_stock=10,
            reserved_stock=0,
            current_cost=1,
            base_unit_id=unit_id,
        )
    )
    db_session.add(
        WorkOrderModel(
            id=work_order_id,
            tenant_id=test_tenant_id,
            wo_number="WO-LIFE",
            product_id=product_id,
            bom_id=bom_id,
            planned_quantity=1,
            produced_quantity=0,
            scrap_quantity=0,
            status="MATERIAL_RESERVED",
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    db_session.add(
        WorkOrderMaterialModel(
            work_order_id=work_order_id,
            material_id=material_id,
            unit_id=unit_id,
            required_quantity=5,
            issued_quantity=0,
        )
    )
    await db_session.flush()

    service = InventoryService(db_session)
    reserved, shortage = await service.reserve_for_work_order(
        tenant_id=test_tenant_id,
        material_id=material_id,
        quantity=Decimal("5"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert reserved == Decimal("5")
    assert shortage == Decimal("0")

    result = await service.issue_material_for_wo(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        material_id=material_id,
        quantity=Decimal("2"),
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert result["work_order_status"] == "MATERIAL_RESERVED"

    reservation = (
        await db_session.execute(select(InventoryReservationModel))
    ).scalar_one()
    assert reservation.status == "PARTIALLY_ISSUED"
    assert Decimal(str(reservation.issued_quantity)) == Decimal("2.000")

    await service.issue_material_for_wo(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        material_id=material_id,
        quantity=Decimal("3"),
        unit_id=unit_id,
        created_by=test_user_id,
    )
    wo = await db_session.get(WorkOrderModel, work_order_id)
    assert wo is not None
    assert wo.status == "MATERIAL_ISSUED"

    await service.consume_stock(
        tenant_id=test_tenant_id,
        material_id=material_id,
        quantity=Decimal("4"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert reservation.status == "PARTIALLY_CONSUMED"
    assert Decimal(str(reservation.consumed_quantity)) == Decimal("4.000")

    await service.consume_stock(
        tenant_id=test_tenant_id,
        material_id=material_id,
        quantity=Decimal("1"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert reservation.status == "CONSUMED"
    assert Decimal(str(reservation.consumed_quantity)) == Decimal("5.000")


@pytest.mark.asyncio
async def test_shortage_record_is_merged_for_idempotent_release(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    service = InventoryService(db_session)
    work_order_id = uuid.uuid4()
    material_id = uuid.uuid4()

    await service.create_shortage_record(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        material_id=material_id,
        required_quantity=Decimal("10"),
        shortage_quantity=Decimal("6"),
        created_by=test_user_id,
    )
    await service.create_shortage_record(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        material_id=material_id,
        required_quantity=Decimal("10"),
        shortage_quantity=Decimal("4"),
        created_by=test_user_id,
    )

    rows = (
        await db_session.execute(select(MaterialShortageModel))
    ).scalars().all()
    assert len(rows) == 1
    assert Decimal(str(rows[0].shortage_quantity)) == Decimal("4.000")


@pytest.mark.asyncio
async def test_batch_partial_consumption_return_lifecycle_preserves_stock(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    material_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    work_order_id = uuid.uuid4()

    db_session.add(
        MaterialModel(
            id=material_id,
            tenant_id=test_tenant_id,
            code="RM-PIPE-12",
            item_code="RM-PIPE-12",
            name="12 inch pipe",
            material_type="raw",
            current_stock=12,
            reserved_stock=0,
            current_cost=1,
            base_unit_id=unit_id,
            is_batch_tracked=True,
        )
    )
    db_session.add(
        BatchModel(
            id=batch_id,
            tenant_id=test_tenant_id,
            material_id=material_id,
            batch_number="SUP-BATCH-12",
            quantity=12,
            original_quantity=12,
            remaining_quantity=12,
            reserved_quantity=0,
            consumed_quantity=0,
            returned_quantity=0,
            status="AVAILABLE",
        )
    )
    db_session.add(
        WorkOrderModel(
            id=work_order_id,
            tenant_id=test_tenant_id,
            wo_number="WO-PIPE",
            product_id=uuid.uuid4(),
            bom_id=uuid.uuid4(),
            planned_quantity=1,
            produced_quantity=0,
            scrap_quantity=0,
            status="MATERIAL_RESERVED",
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    db_session.add(
        WorkOrderMaterialModel(
            work_order_id=work_order_id,
            material_id=material_id,
            unit_id=unit_id,
            required_quantity=4,
            issued_quantity=0,
        )
    )
    await db_session.flush()

    service = InventoryService(db_session)
    reserved, shortage = await service.reserve_for_work_order(
        tenant_id=test_tenant_id,
        material_id=material_id,
        quantity=Decimal("4"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert reserved == Decimal("4")
    assert shortage == Decimal("0")

    material = await db_session.get(MaterialModel, material_id)
    batch = await db_session.get(BatchModel, batch_id)
    assert Decimal(str(material.current_stock)) == Decimal("12.000")
    assert Decimal(str(material.reserved_stock)) == Decimal("4.000")
    assert Decimal(str(batch.remaining_quantity)) == Decimal("12.0000")
    assert Decimal(str(batch.reserved_quantity)) == Decimal("4.0000")

    await service.issue_material_for_wo(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        material_id=material_id,
        quantity=Decimal("4"),
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert Decimal(str(material.current_stock)) == Decimal("8.000")
    assert Decimal(str(material.reserved_stock)) == Decimal("0")
    assert Decimal(str(batch.remaining_quantity)) == Decimal("8.0000")
    assert Decimal(str(batch.reserved_quantity)) == Decimal("0")

    await service.consume_stock(
        tenant_id=test_tenant_id,
        material_id=material_id,
        quantity=Decimal("3"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert Decimal(str(material.current_stock)) == Decimal("8.000")
    assert Decimal(str(batch.consumed_quantity)) == Decimal("3.0000")

    before_failed_tx_count = await db_session.scalar(select(func.count()).select_from(InventoryTransactionModel))
    with pytest.raises(ValueError):
        await service.consume_stock(
            tenant_id=test_tenant_id,
            material_id=material_id,
            quantity=Decimal("2"),
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=test_user_id,
        )
    after_failed_tx_count = await db_session.scalar(select(func.count()).select_from(InventoryTransactionModel))
    assert after_failed_tx_count == before_failed_tx_count

    await service.return_stock(
        tenant_id=test_tenant_id,
        material_id=material_id,
        quantity=Decimal("1"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    reservation = (
        await db_session.execute(select(InventoryReservationModel))
    ).scalar_one()
    wo_material = (
        await db_session.execute(select(WorkOrderMaterialModel))
    ).scalar_one()
    assert Decimal(str(material.current_stock)) == Decimal("9.000")
    assert Decimal(str(batch.remaining_quantity)) == Decimal("9.0000")
    assert Decimal(str(batch.returned_quantity)) == Decimal("1.0000")
    assert Decimal(str(reservation.issued_quantity)) == Decimal("4.000")
    assert Decimal(str(reservation.consumed_quantity)) == Decimal("3.000")
    assert Decimal(str(reservation.returned_quantity)) == Decimal("1.000")
    assert Decimal(str(wo_material.issued_quantity)) == Decimal("3.000")

    before_failed_tx_count = await db_session.scalar(select(func.count()).select_from(InventoryTransactionModel))
    with pytest.raises(ValueError):
        await service.return_stock(
            tenant_id=test_tenant_id,
            material_id=material_id,
            quantity=Decimal("1"),
            work_order_id=work_order_id,
            unit_id=unit_id,
            created_by=test_user_id,
        )
    after_failed_tx_count = await db_session.scalar(select(func.count()).select_from(InventoryTransactionModel))
    assert after_failed_tx_count == before_failed_tx_count


@pytest.mark.asyncio
async def test_finished_goods_receipt_is_idempotent(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    product_id = uuid.uuid4()
    work_order_id = uuid.uuid4()
    unit_id = uuid.uuid4()

    db_session.add(
        MaterialModel(
            id=product_id,
            tenant_id=test_tenant_id,
            code="FG-IDEMP",
            item_code="FG-IDEMP",
            name="Finished Good",
            material_type="finished_good",
            current_stock=0,
            reserved_stock=0,
            current_cost=1,
            base_unit_id=unit_id,
        )
    )
    db_session.add(
        WorkOrderModel(
            id=work_order_id,
            tenant_id=test_tenant_id,
            wo_number="WO-FG-IDEMP",
            product_id=product_id,
            bom_id=uuid.uuid4(),
            planned_quantity=2,
            produced_quantity=2,
            scrap_quantity=0,
            status="QC_APPROVED",
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    await db_session.flush()

    service = InventoryService(db_session)
    first_receipt = await service.receive_fg(
        tenant_id=test_tenant_id,
        product_id=product_id,
        quantity=Decimal("2"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    second_receipt = await service.receive_fg(
        tenant_id=test_tenant_id,
        product_id=product_id,
        quantity=Decimal("2"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )

    product = await db_session.get(MaterialModel, product_id)
    fg_receipts = await db_session.scalar(
        select(func.count())
        .select_from(InventoryTransactionModel)
        .where(
            InventoryTransactionModel.material_id == product_id,
            InventoryTransactionModel.reference_id == work_order_id,
            InventoryTransactionModel.transaction_type == "FG_RECEIPT",
        )
    )
    assert first_receipt is True
    assert second_receipt is False
    assert Decimal(str(product.current_stock)) == Decimal("2.000")
    assert fg_receipts == 1
