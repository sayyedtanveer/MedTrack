"""Worker dashboard API routes."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session
from backend.app.application.manufacturing.services.production_execution_service import ProductionExecutionService
from backend.app.application.manufacturing.handlers.worker_handler import WorkerHandler
from backend.app.application.manufacturing.commands.worker_commands import (
    StartOperationCommand,
    PauseOperationCommand,
    ResumeOperationCommand,
    CompleteOperationCommand,
    ReportWastageCommand,
    RecordProductionCommand,
)
from backend.app.interfaces.api.v1.schemas.worker_schemas import (
    WorkerQueueResponse,
    JobCardResponse,
    StartOperationRequest,
    PauseOperationRequest,
    ResumeOperationRequest,
    CompleteOperationRequest,
    ReportWastageRequest,
    RecordProductionRequest,
)

router = APIRouter(prefix="/worker", tags=["Worker"])


# ── Worker Dashboard Queues ─────────────────────────────────────────────────────

@router.get("/queue", response_model=list[WorkerQueueResponse])
async def get_worker_queue(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get assigned work orders and operations for worker dashboard."""
    production_service = ProductionExecutionService(session)
    queue = await production_service.get_worker_queue(tenant_id=tenant_id, user_id=user_id)
    return queue


# ── Worker Actions ─────────────────────────────────────────────────────────────

@router.post("/start-operation")
async def start_operation(
    body: StartOperationRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    assigned_to: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Start a job card operation.
    
    Triggers WO transition: MATERIAL_ISSUED → IN_PRODUCTION (if first operation).
    """
    command = StartOperationCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        job_card_id=body.job_card_id,
        assigned_to=assigned_to,
    )
    
    handler = WorkerHandler(session)
    await handler.handle_start_operation(command)
    
    await session.commit()
    return {"status": "success", "message": "Operation started"}


@router.post("/pause-operation")
async def pause_operation(
    body: PauseOperationRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Pause a job card operation."""
    command = PauseOperationCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        job_card_id=body.job_card_id,
        pause_reason=body.pause_reason,
        operator_notes=body.operator_notes,
    )
    
    handler = WorkerHandler(session)
    await handler.handle_pause_operation(command)
    
    await session.commit()
    return {"status": "success", "message": "Operation paused"}


@router.post("/resume-operation")
async def resume_operation(
    body: ResumeOperationRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Resume a paused job card operation."""
    command = ResumeOperationCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        job_card_id=body.job_card_id,
        operator_notes=body.operator_notes,
    )

    handler = WorkerHandler(session)
    await handler.handle_resume_operation(command)

    await session.commit()
    return {"status": "success", "message": "Operation resumed"}


@router.post("/complete-operation")
async def complete_operation(
    body: CompleteOperationRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Complete a job card operation."""
    command = CompleteOperationCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        job_card_id=body.job_card_id,
        remarks=body.remarks,
        operator_notes=body.operator_notes,
        produced_quantity=body.produced_quantity,
        scrap_quantity=body.scrap_quantity,
        rework_quantity=body.rework_quantity,
        rejected_quantity=body.rejected_quantity,
    )
    
    handler = WorkerHandler(session)
    await handler.handle_complete_operation(command)
    
    await session.commit()
    return {"status": "success", "message": "Operation completed"}


@router.post("/report-wastage")
async def report_wastage(
    body: ReportWastageRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    recorded_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Report scrap/wastage during production.
    
    Inventory impact: CONSUMED → REJECTED.
    """
    command = ReportWastageCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        scrap_quantity=body.scrap_quantity,
        recorded_by=recorded_by,
        notes=body.notes,
    )
    
    handler = WorkerHandler(session)
    await handler.handle_report_wastage(command)
    
    await session.commit()
    return {"status": "success", "message": "Wastage reported"}


@router.post("/record-production")
async def record_production(
    body: RecordProductionRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    recorded_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Record production quantity.
    
    Triggers WO transition: IN_PRODUCTION → QC_PENDING.
    Inventory impact: ISSUED → CONSUMED.
    """
    command = RecordProductionCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        produced_quantity=body.produced_quantity,
        scrap_quantity=body.scrap_quantity,
        job_card_id=body.job_card_id,
        operation_id=body.operation_id,
        recorded_by=recorded_by,
        notes=body.notes,
    )
    
    handler = WorkerHandler(session)
    await handler.handle_record_production(command)
    
    await session.commit()
    return {"status": "success", "message": "Production recorded"}
