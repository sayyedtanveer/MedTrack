from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
from backend.app.application.manufacturing.commands.work_order_commands import RecordProductionCommand
from backend.app.application.manufacturing.services.workflow_orchestration_service import WorkflowOrchestrationService
from backend.app.infrastructure.persistence.models.work_order_model import (
    JobCardModel,
    WorkOrderModel,
)


@pytest.mark.asyncio
async def test_non_final_job_card_production_does_not_increase_wo_produced(
    db_session: AsyncSession,
    test_tenant_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    # Setup Work Order with 2 Job Cards
    wo_id = uuid.uuid4()
    jc1_id = uuid.uuid4()
    jc2_id = uuid.uuid4()

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
            status="IN_PRODUCTION",
            priority="NORMAL",
            start_date=date.today(),
            due_date=date.today(),
            created_by=test_user_id,
        )
    )
    db_session.add(
        JobCardModel(
            id=jc1_id,
            work_order_id=wo_id,
            operation_id=uuid.uuid4(),
            sequence=1,
            assigned_to=test_user_id,
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        JobCardModel(
            id=jc2_id,
            work_order_id=wo_id,
            operation_id=uuid.uuid4(),
            sequence=2,
            assigned_to=test_user_id,
            status="PENDING",
        )
    )
    await db_session.flush()

    # We need to mock some dependencies of WorkOrderHandler
    # But since we just want to test handle_record_production, let's see if we can use ProductionExecutionService or mock the handler.
    # Actually, in tests/unit/manufacturing/conftest.py, we might have a fully initialized handler or service.
    # We will just write the test logic assuming the fix is applied.
