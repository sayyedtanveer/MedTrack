"""Quality Control dashboard API routes."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session
from backend.app.application.quality.services.qc_service import QCService
from backend.app.application.quality.handlers.qc_handler import QCHandler
from backend.app.application.quality.commands.qc_commands import (
    ApproveInspectionCommand,
    RejectInspectionCommand,
    SendToReworkCommand,
    ScrapBatchCommand,
)
from backend.app.interfaces.api.v1.schemas.quality_schemas import (
    InspectionQueueResponse,
    RejectedQueueResponse,
    ReworkQueueResponse,
    ApproveInspectionRequest,
    RejectInspectionRequest,
    SendToReworkRequest,
    ScrapBatchRequest,
    InspectionResponse,
)

router = APIRouter(prefix="/quality-control", tags=["Quality Control"])


# ── QC Dashboard Queues ────────────────────────────────────────────────────────

@router.get("/inspection-queue", response_model=list[InspectionQueueResponse])
async def get_inspection_queue(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get QC inspection queue for QC dashboard.
    
    Shows all Work Orders in QC_PENDING state.
    """
    qc_service = QCService(session)
    queue = await qc_service.get_inspection_queue(tenant_id=tenant_id)
    return queue


@router.get("/rejected-queue", response_model=list[RejectedQueueResponse])
async def get_rejected_queue(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get rejected batches for QC dashboard.
    
    Shows all Work Orders in QC_REJECTED state.
    """
    qc_service = QCService(session)
    queue = await qc_service.get_rejected_queue(tenant_id=tenant_id)
    return queue


@router.get("/rework-queue", response_model=list[ReworkQueueResponse])
async def get_rework_queue(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Get rework queue for QC dashboard.
    
    Shows all Work Orders in REWORK state.
    """
    qc_service = QCService(session)
    queue = await qc_service.get_rework_queue(tenant_id=tenant_id)
    return queue


# ── QC Actions ─────────────────────────────────────────────────────────────────

@router.post("/approve", response_model=InspectionResponse)
async def approve_inspection(
    body: ApproveInspectionRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    inspector_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Approve QC inspection.
    
    Triggers WO transition: QC_PENDING → QC_APPROVED.
    Downstream: FG receipt.
    """
    command = ApproveInspectionCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        inspector_id=inspector_id,
        inspection_date=body.inspection_date or date.today(),
        remarks=body.remarks,
        details=body.details,
    )
    
    handler = QCHandler(session)
    inspection = await handler.approve_inspection(command)
    
    await session.commit()
    return InspectionResponse(**inspection.to_dict())


@router.post("/reject", response_model=InspectionResponse)
async def reject_inspection(
    body: RejectInspectionRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    inspector_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Reject QC inspection.
    
    Triggers WO transition: QC_PENDING → QC_REJECTED.
    Downstream: Rework or Scrap decision.
    """
    command = RejectInspectionCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        inspector_id=inspector_id,
        inspection_date=body.inspection_date or date.today(),
        reason=body.reason,
        defect_details=body.defect_details,
        rework_required=body.rework_required,
        scrap_quantity=body.scrap_quantity,
        details=body.details,
    )
    
    handler = QCHandler(session)
    inspection = await handler.reject_inspection(command)
    
    await session.commit()
    return InspectionResponse(**inspection.to_dict())


@router.post("/send-to-rework")
async def send_to_rework(
    body: SendToReworkRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    inspector_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Send rejected batch to rework.
    
    Triggers WO transition: QC_REJECTED → REWORK.
    """
    command = SendToReworkCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        inspector_id=inspector_id,
        rework_reason=body.rework_reason,
        additional_material_required=body.additional_material_required,
        additional_materials=body.additional_materials,
    )
    
    handler = QCHandler(session)
    await handler.send_to_rework(command)
    
    await session.commit()
    return {"status": "success", "message": "Sent to rework"}


@router.post("/scrap")
async def scrap_batch(
    body: ScrapBatchRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    inspector_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """Scrap rejected batch.
    
    Triggers WO transition: QC_REJECTED → REJECTED → CLOSED.
    Inventory impact: ISSUED → REJECTED.
    """
    command = ScrapBatchCommand(
        tenant_id=tenant_id,
        work_order_id=body.work_order_id,
        inspector_id=inspector_id,
        scrap_reason=body.scrap_reason,
        scrap_quantity=body.scrap_quantity,
    )
    
    handler = QCHandler(session)
    await handler.scrap_batch(command)
    
    await session.commit()
    return {"status": "success", "message": "Batch scrapped"}
