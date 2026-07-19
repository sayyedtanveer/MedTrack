from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.manufacturing.services.production_execution_service import (
    ProductionExecutionService,
)
from backend.app.infrastructure.persistence.models.bom_model import BOMLineModel, BOMModel
from backend.app.infrastructure.persistence.models.inventory_reservation_model import (
    InventoryReservationModel,
)
from backend.app.infrastructure.persistence.models.material_consumption_model import (
    MaterialConsumptionRecordModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.work_order_model import (
    JobCardModel,
    WorkOrderMaterialModel,
    WorkOrderModel,
)


@pytest.mark.asyncio
async def test_pause_resume_tracks_downtime_and_notes(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    work_order_id = uuid.uuid4()
    job_card_id = uuid.uuid4()

    db_session.add(
        WorkOrderModel(
            id=work_order_id,
            tenant_id=test_tenant_id,
            wo_number="WO-DOWNTIME",
            product_id=uuid.uuid4(),
            bom_id=uuid.uuid4(),
            planned_quantity=5,
            produced_quantity=0,
            scrap_quantity=0,
            status="IN_PRODUCTION",
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    db_session.add(
        JobCardModel(
            id=job_card_id,
            work_order_id=work_order_id,
            operation_id=uuid.uuid4(),
            sequence=1,
            assigned_to=test_user_id,
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
    )
    await db_session.flush()

    service = ProductionExecutionService(db_session)
    await service.pause_operation(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        job_card_id=job_card_id,
        pause_reason="Machine setup",
        operator_notes="Waiting for fixture",
    )

    job_card = await db_session.get(JobCardModel, job_card_id)
    assert job_card is not None
    assert job_card.status == "PAUSED"
    assert job_card.pause_reason == "Machine setup"
    assert "Waiting for fixture" in (job_card.operator_notes or "")

    job_card.paused_at = datetime.now(timezone.utc) - timedelta(seconds=75)
    await service.resume_operation(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        job_card_id=job_card_id,
        operator_notes="Fixture ready",
    )

    assert job_card.status == "IN_PROGRESS"
    assert job_card.paused_at is None
    assert Decimal(str(job_card.total_downtime_seconds)) >= Decimal("75")
    assert "Fixture ready" in (job_card.operator_notes or "")


@pytest.mark.asyncio
async def test_bom_scrap_consumption_is_incremental_and_gates_qc_until_planned_output(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    material_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    product_id = uuid.uuid4()
    bom_id = uuid.uuid4()
    work_order_id = uuid.uuid4()
    job_card_id = uuid.uuid4()
    operation_id = uuid.uuid4()

    db_session.add(
        MaterialModel(
            id=material_id,
            tenant_id=test_tenant_id,
            code="RM-BOM-SCRAP",
            item_code="RM-BOM-SCRAP",
            name="BOM Scrap Material",
            material_type="raw",
            current_stock=20,
            reserved_stock=0,
            current_cost=1,
            base_unit_id=unit_id,
        )
    )
    db_session.add(
        BOMModel(
            id=bom_id,
            tenant_id=test_tenant_id,
            variant_id=product_id,
            version="v1",
            is_active=True,
            valid_from=datetime.now(timezone.utc),
            created_by=test_user_id,
        )
    )
    db_session.add(
        BOMLineModel(
            tenant_id=test_tenant_id,
            bom_id=bom_id,
            material_id=material_id,
            quantity=2,
            scrap_percentage=10,
            unit_id=unit_id,
        )
    )
    db_session.add(
        WorkOrderModel(
            id=work_order_id,
            tenant_id=test_tenant_id,
            wo_number="WO-BOM-SCRAP",
            product_id=product_id,
            bom_id=bom_id,
            planned_quantity=5,
            produced_quantity=0,
            scrap_quantity=0,
            status="IN_PRODUCTION",
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
            required_quantity=11,
            issued_quantity=0,
        )
    )
    db_session.add(
        JobCardModel(
            id=job_card_id,
            work_order_id=work_order_id,
            operation_id=operation_id,
            sequence=1,
            assigned_to=test_user_id,
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc),
        )
    )
    await db_session.flush()

    inventory = InventoryService(db_session)
    reserved, shortage = await inventory.reserve_for_work_order(
        tenant_id=test_tenant_id,
        material_id=material_id,
        quantity=Decimal("11"),
        work_order_id=work_order_id,
        unit_id=unit_id,
        created_by=test_user_id,
    )
    assert reserved == Decimal("11")
    assert shortage == Decimal("0")
    await inventory.issue_material_for_wo(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        material_id=material_id,
        quantity=Decimal("11"),
        unit_id=unit_id,
        created_by=test_user_id,
        transition_wo_status=False,
    )

    service = ProductionExecutionService(db_session)
    await service.record_production(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        produced_quantity=Decimal("2"),
        scrap_quantity=Decimal("0"),
        job_card_id=job_card_id,
        recorded_by=test_user_id,
        notes="Partial production",
    )

    wo = await db_session.get(WorkOrderModel, work_order_id)
    assert wo is not None
    assert wo.status == "IN_PRODUCTION"

    consumed_total = (
        await db_session.execute(
            select(func.coalesce(func.sum(MaterialConsumptionRecordModel.actual_quantity), 0))
        )
    ).scalar_one()
    assert Decimal(str(consumed_total)) == Decimal("4.400")

    reservation = (
        await db_session.execute(select(InventoryReservationModel))
    ).scalar_one()
    assert Decimal(str(reservation.consumed_quantity)) == Decimal("4.400")

    await service.record_production(
        tenant_id=test_tenant_id,
        work_order_id=work_order_id,
        produced_quantity=Decimal("5"),
        scrap_quantity=Decimal("0"),
        job_card_id=job_card_id,
        recorded_by=test_user_id,
        notes="Planned quantity complete",
    )

    wo = await db_session.get(WorkOrderModel, work_order_id)
    assert wo is not None
    assert wo.status == "QC_PENDING"

    consumed_total = (
        await db_session.execute(
            select(func.coalesce(func.sum(MaterialConsumptionRecordModel.actual_quantity), 0))
        )
    ).scalar_one()
    assert Decimal(str(consumed_total)) == Decimal("11.000")
    assert Decimal(str(reservation.consumed_quantity)) == Decimal("11.000")

    job_card = await db_session.get(JobCardModel, job_card_id)
    assert job_card is not None
    assert Decimal(str(job_card.produced_quantity)) == Decimal("5")
    assert "Planned quantity complete" in (job_card.operator_notes or "")
