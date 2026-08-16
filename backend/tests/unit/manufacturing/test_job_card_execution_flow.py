from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
from backend.app.application.manufacturing.commands.work_order_commands import (
    RecordProductionCommand, StartJobCardCommand, CompleteWorkOrderCommand
)
from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus
from backend.app.infrastructure.persistence.models.work_order_model import (
    JobCardModel, WorkOrderModel
)


@pytest.mark.asyncio
async def test_record_production_requires_job_card_if_present(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    wo_id = uuid.uuid4()
    db_session.add(
        WorkOrderModel(
            id=wo_id,
            tenant_id=test_tenant_id,
            wo_number="WO-TEST-1",
            product_id=uuid.uuid4(),
            bom_id=uuid.uuid4(),
            planned_quantity=10,
            produced_quantity=0,
            scrap_quantity=0,
            status=WorkOrderStatus.IN_PRODUCTION.value,
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    db_session.add(
        JobCardModel(
            id=uuid.uuid4(),
            work_order_id=wo_id,
            operation_id=uuid.uuid4(),
            sequence=1,
            status="PENDING",
        )
    )
    await db_session.flush()

    handler = WorkOrderHandler(db_session)
    cmd = RecordProductionCommand(
        tenant_id=test_tenant_id,
        work_order_id=wo_id,
        produced_quantity=5,
        scrap_quantity=0,
        recorded_by=test_user_id,
    )
    
    with pytest.raises(ValueError, match="must be associated with a specific Job Card"):
        await handler.handle_record_production(cmd)


@pytest.mark.asyncio
async def test_start_job_card_enforces_sequence(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    wo_id = uuid.uuid4()
    jc1_id = uuid.uuid4()
    jc2_id = uuid.uuid4()

    db_session.add(
        WorkOrderModel(
            id=wo_id,
            tenant_id=test_tenant_id,
            wo_number="WO-TEST-2",
            product_id=uuid.uuid4(),
            bom_id=uuid.uuid4(),
            planned_quantity=10,
            produced_quantity=0,
            scrap_quantity=0,
            status=WorkOrderStatus.MATERIAL_ISSUED.value,
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    db_session.add_all([
        JobCardModel(
            id=jc1_id,
            work_order_id=wo_id,
            operation_id=uuid.uuid4(),
            sequence=1,
            status="PENDING",
        ),
        JobCardModel(
            id=jc2_id,
            work_order_id=wo_id,
            operation_id=uuid.uuid4(),
            sequence=2,
            status="PENDING",
        )
    ])
    await db_session.flush()

    handler = WorkOrderHandler(db_session)
    
    # Try starting OP-2 before OP-1 is DONE
    cmd2 = StartJobCardCommand(
        tenant_id=test_tenant_id,
        work_order_id=wo_id,
        job_card_id=jc2_id,
        assigned_to=test_user_id
    )
    with pytest.raises(ValueError, match="Complete OP-1 before starting OP-2"):
        await handler.handle_start_job_card(cmd2)

    # Start OP-1 should succeed
    cmd1 = StartJobCardCommand(
        tenant_id=test_tenant_id,
        work_order_id=wo_id,
        job_card_id=jc1_id,
        assigned_to=test_user_id
    )
    await handler.handle_start_job_card(cmd1)
    
    jc1 = await db_session.get(JobCardModel, jc1_id)
    assert jc1.status == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_submit_qc_requires_all_job_cards_done(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    wo_id = uuid.uuid4()
    db_session.add(
        WorkOrderModel(
            id=wo_id,
            tenant_id=test_tenant_id,
            wo_number="WO-TEST-3",
            product_id=uuid.uuid4(),
            bom_id=uuid.uuid4(),
            planned_quantity=10,
            produced_quantity=10, # Has produced quantity
            scrap_quantity=0,
            status=WorkOrderStatus.IN_PRODUCTION.value,
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    db_session.add(
        JobCardModel(
            id=uuid.uuid4(),
            work_order_id=wo_id,
            operation_id=uuid.uuid4(),
            sequence=1,
            status="IN_PROGRESS", # Not DONE
        )
    )
    await db_session.flush()

    handler = WorkOrderHandler(db_session)
    cmd = CompleteWorkOrderCommand(
        tenant_id=test_tenant_id,
        work_order_id=wo_id,
    )
    
    with pytest.raises(ValueError, match="Complete all manufacturing operations before sending"):
        await handler.handle_complete(cmd)
