"""Work Order & Shop Floor REST API endpoints."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.work_order_schemas import (
    WorkOrderCreateRequest, IssueMaterialRequest, RecordProductionRequest,
    StartJobCardRequest, CompleteJobCardRequest,
    WorkOrderSummary, WorkOrderDetail, JobCardResponse, WorkOrderErrorResponse,
    MaterialAvailabilityResponse,
)
from backend.app.application.manufacturing.commands.work_order_commands import (
    CreateWorkOrderCommand, ReleaseWorkOrderCommand, StartWorkOrderCommand,
    IssueMaterialCommand, RecordProductionCommand,
    CompleteWorkOrderCommand, CloseWorkOrderCommand,
    StartJobCardCommand, CompleteJobCardCommand,
    QCApproveCommand, QCRejectCommand, QCSendToReworkCommand, FGReceiveCommand,
)
from backend.app.application.manufacturing.commands.worker_commands import (
    StartOperationCommand, PauseOperationCommand, ResumeOperationCommand,
    CompleteOperationCommand, ReportWastageCommand,
)
from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
from backend.app.application.manufacturing.handlers.worker_handler import WorkerHandler
from backend.app.application.manufacturing.services.material_availability_service import (
    MaterialAvailabilityService,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.domain.manufacturing.exceptions import (
    InsufficientStockError, MaterialNotIssuedError, BOMNotFoundError, WorkOrderImmutableError
)
from backend.app.domain.manufacturing.entities.work_order import InvalidStatusTransitionError

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.infrastructure.persistence.models.work_order_model import (
    WorkOrderModel, JobCardModel
)
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.interfaces.api.v1.dependencies.auth import get_container


router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


def _get_handler(request: Request):
    container = get_container(request)
    return container.session_factory


async def _error_response(exc: Exception) -> JSONResponse:
    """Map domain exceptions to structured error payloads."""
    code = getattr(exc, "error_code", "INTERNAL_ERROR")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error_code": code, "message": str(exc), "validation_errors": []},
    )


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("manufacturing:write"))])
async def create_work_order(
    body: WorkOrderCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = CreateWorkOrderCommand(
                tenant_id=tenant_id, created_by=user_id, **body.model_dump()
            )
            wo_id = await handler.handle_create(cmd)
            await uow.commit()
            return {"id": str(wo_id)}
        except (BOMNotFoundError, ValueError) as e:
            return await _error_response(e)


@router.get("", response_model=List[WorkOrderSummary], dependencies=[Depends(require_permission("manufacturing:read"))])
async def list_work_orders(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    status_filter: Optional[str] = Query(None, alias="status"),
    active: Optional[bool] = Query(
        None,
        description="When true, return shop-floor active WOs (material + production states)",
    ),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
):
    from backend.app.domain.manufacturing.entities.work_order import WorkOrderStatus

    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(WorkOrderModel).where(
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
        if active:
            active_statuses = [
                WorkOrderStatus.MATERIAL_RESERVED.value,
                WorkOrderStatus.MATERIAL_ISSUED.value,
                WorkOrderStatus.IN_PRODUCTION.value,
                WorkOrderStatus.REWORK.value,
            ]
            stmt = stmt.where(WorkOrderModel.status.in_(active_statuses))
        elif status_filter:
            # Legacy alias: IN_PROGRESS → IN_PRODUCTION
            normalized = (
                WorkOrderStatus.IN_PRODUCTION.value
                if status_filter == "IN_PROGRESS"
                else status_filter
            )
            stmt = stmt.where(WorkOrderModel.status == normalized)
        if product_id:
            stmt = stmt.where(WorkOrderModel.product_id == product_id)
        stmt = stmt.order_by(WorkOrderModel.created_at.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [WorkOrderSummary.model_validate(r) for r in rows]


@router.get(
    "/planner/shortage-queue",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def planner_shortage_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Work orders awaiting material (MATERIAL_PENDING) for planner dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.manufacturing.services.planner_service import PlannerService

        service = PlannerService(session)
        return await service.get_shortage_queue(tenant_id=tenant_id)


@router.get(
    "/material-availability",
    response_model=MaterialAvailabilityResponse,
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def preview_material_availability(
    request: Request,
    product_id: uuid.UUID = Query(...),
    quantity: Decimal = Query(..., gt=0),
    bom_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        service = MaterialAvailabilityService(session)
        try:
            preview = await service.check_material_availability(
                tenant_id=tenant_id,
                product_id=product_id,
                quantity=quantity,
                bom_id=bom_id,
            )
            return MaterialAvailabilityResponse.model_validate(preview)
        except BOMNotFoundError as exc:
            return await _error_response(exc)


@router.get("/{work_order_id}", response_model=WorkOrderDetail, dependencies=[Depends(require_permission("manufacturing:read"))])
async def get_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(WorkOrderModel)
            .options(
                selectinload(WorkOrderModel.materials),
                selectinload(WorkOrderModel.job_cards),
            )
            .where(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await session.execute(stmt)
        wo = result.scalar_one_or_none()
        if not wo:
            return JSONResponse(status_code=404, content={"error_code": "NOT_FOUND", "message": "Work Order not found", "validation_errors": []})
        return WorkOrderDetail.model_validate(wo)


@router.post("/{work_order_id}/release", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def release_work_order(
    work_order_id: uuid.UUID,
    request: Request,
):
    container = get_container(request)
    # tenant_id is available in request.state.tenant_id from auth dependency
    tenant_id = request.state.tenant_id
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_release(ReleaseWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            wo = await session.get(WorkOrderModel, work_order_id)
            await uow.commit()
            return {"status": wo.status if wo is not None else "RELEASED"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.post("/{work_order_id}/allocate-materials", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def allocate_materials(
    work_order_id: uuid.UUID,
    request: Request,
):
    container = get_container(request)
    # tenant_id is available in request.state.tenant_id from auth dependency
    tenant_id = request.state.tenant_id
    async with container.session_factory() as session:
        from backend.app.application.manufacturing.commands.work_order_commands import AllocateMaterialsCommand
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_allocate_materials(AllocateMaterialsCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            wo = await session.get(WorkOrderModel, work_order_id)
            await uow.commit()
            return {"status": wo.status if wo is not None else "MATERIAL_PENDING"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.post("/{work_order_id}/start", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def start_work_order(
    work_order_id: uuid.UUID,
    request: Request,
):
    container = get_container(request)
    # tenant_id is available in request.state.tenant_id from auth dependency
    tenant_id = request.state.tenant_id
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_start(StartWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "IN_PRODUCTION"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.post("/{work_order_id}/issue-materials", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def issue_materials(
    work_order_id: uuid.UUID,
    body: IssueMaterialRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = IssueMaterialCommand(
                tenant_id=tenant_id, work_order_id=work_order_id, issued_by=user_id, **body.model_dump()
            )
            await handler.handle_issue_material(cmd)
            await uow.commit()
            return {"message": "Material issued"}
        except (InsufficientStockError, InvalidStatusTransitionError, ValueError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/record-production", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def record_production(
    work_order_id: uuid.UUID,
    body: RecordProductionRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = RecordProductionCommand(
                tenant_id=tenant_id, work_order_id=work_order_id, recorded_by=user_id, **body.model_dump()
            )
            await handler.handle_record_production(cmd)
            await uow.commit()
            return {"message": "Production recorded"}
        except (InsufficientStockError, ValueError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/complete", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def complete_work_order(
    work_order_id: uuid.UUID,
    request: Request,
):
    container = get_container(request)
    # tenant_id is available in request.state.tenant_id from auth dependency
    tenant_id = request.state.tenant_id
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_complete(CompleteWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "COMPLETED"}
        except (InvalidStatusTransitionError, MaterialNotIssuedError) as e:
            return await _error_response(e)


@router.post("/{work_order_id}/close", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def close_work_order(
    work_order_id: uuid.UUID,
    request: Request,
):
    container = get_container(request)
    # tenant_id is available in request.state.tenant_id from auth dependency
    tenant_id = request.state.tenant_id
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            await handler.handle_close(CloseWorkOrderCommand(tenant_id=tenant_id, work_order_id=work_order_id))
            await uow.commit()
            return {"status": "CLOSED"}
        except InvalidStatusTransitionError as e:
            return await _error_response(e)


@router.get("/{work_order_id}/job-cards", response_model=List[JobCardResponse], dependencies=[Depends(require_permission("manufacturing:read"))])
async def list_job_cards(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(JobCardModel)
            .join(WorkOrderModel, JobCardModel.work_order_id == WorkOrderModel.id)
            .where(
                JobCardModel.work_order_id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
            )
            .order_by(JobCardModel.sequence)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        
        # Build response with operation_name from relationship
        job_cards_data = []
        for jc in rows:
            produced = Decimal(str(jc.produced_quantity or 0))
            scrap = Decimal(str(jc.scrap_quantity or 0))
            rejected = Decimal(str(jc.rejected_quantity or 0))
            total_output = produced + scrap + rejected
            yield_percent = float((produced / total_output) * Decimal("100")) if total_output > 0 else 0.0
            duration = None
            if jc.started_at and jc.completed_at:
                started_at = jc.started_at
                completed_at = jc.completed_at
                if started_at.tzinfo is None and completed_at.tzinfo is not None:
                    completed_at = completed_at.replace(tzinfo=None)
                elif started_at.tzinfo is not None and completed_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=None)
                duration = max(0.0, (completed_at - started_at).total_seconds())
                duration -= float(Decimal(str(jc.total_downtime_seconds or 0)))
            job_cards_data.append({
                "id": str(jc.id),
                "operation_id": str(jc.operation_id),
                "operation_name": jc.operation.name if jc.operation else "",
                "sequence": jc.sequence,
                "status": jc.status,
                "assigned_to": str(jc.assigned_to) if jc.assigned_to else None,
                "started_at": jc.started_at.isoformat() if jc.started_at else None,
                "paused_at": jc.paused_at.isoformat() if jc.paused_at else None,
                "completed_at": jc.completed_at.isoformat() if jc.completed_at else None,
                "total_downtime_seconds": float(Decimal(str(jc.total_downtime_seconds or 0))),
                "actual_duration_seconds": duration,
                "produced_quantity": float(produced),
                "scrap_quantity": float(scrap),
                "rework_quantity": float(Decimal(str(jc.rework_quantity or 0))),
                "rejected_quantity": float(rejected),
                "yield_percent": round(yield_percent, 2),
                "progress_percent": 100.0 if jc.status in ("DONE", "COMPLETED") else (50.0 if jc.status == "IN_PROGRESS" else (40.0 if jc.status == "PAUSED" else 0.0)),
                "pause_reason": jc.pause_reason,
                "operator_notes": jc.operator_notes,
                "remarks": jc.remarks,
            })
        return job_cards_data


@router.patch("/{work_order_id}/job-cards/{job_card_id}/start", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def start_job_card(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    body: StartJobCardRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = StartJobCardCommand(
                tenant_id=tenant_id, work_order_id=work_order_id,
                job_card_id=job_card_id, **body.model_dump()
            )
            await handler.handle_start_job_card(cmd)
            await uow.commit()
            return {"status": "IN_PRODUCTION"}
        except ValueError as e:
            return await _error_response(e)


@router.get("/{work_order_id}/material-consumption", dependencies=[Depends(require_permission("manufacturing:read"))])
async def get_work_order_consumption(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get the material consumption history for this Work Order."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(InventoryTransactionModel, MaterialModel.code, MaterialModel.name)
            .join(MaterialModel, MaterialModel.id == InventoryTransactionModel.material_id)
            .where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.reference_type == "work_order",
                InventoryTransactionModel.reference_id == work_order_id,
                InventoryTransactionModel.transaction_type.in_(("issue", "CONSUME", "consume")),
                InventoryTransactionModel.is_deleted.is_(False),
            )
            .order_by(InventoryTransactionModel.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = result.all()

    return [
        {
            "id": str(tx.id),
            "material_id": str(tx.material_id),
            "material_code": code,
            "material_name": name,
            "quantity": float(tx.quantity),
            "created_at": tx.created_at.isoformat(),
            "remarks": tx.remarks,
        }
        for tx, code, name in rows
    ]
@router.patch("/{work_order_id}/job-cards/{job_card_id}/complete", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("manufacturing:write"))])
async def complete_job_card(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    body: CompleteJobCardRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = WorkOrderHandler(session).with_uow(uow)
        try:
            cmd = CompleteJobCardCommand(
                tenant_id=tenant_id, work_order_id=work_order_id,
                job_card_id=job_card_id, **body.model_dump()
            )
            await handler.handle_complete_job_card(cmd)
            await uow.commit()
            return {"status": "DONE"}
        except ValueError as e:
            return await _error_response(e)


# ── Phase 4: Worker Operational Flow ───────────────────────────────────────

@router.get("/worker/queue")
async def get_worker_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get assigned work orders and operations for worker dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.manufacturing.services.production_execution_service import ProductionExecutionService
        service = ProductionExecutionService(session)
        queue = await service.get_worker_queue(tenant_id=tenant_id, user_id=user_id)
        return queue


@router.post("/{work_order_id}/job-cards/{job_card_id}/start-operation", status_code=status.HTTP_200_OK)
async def start_operation(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Start a job card operation."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = StartOperationCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            job_card_id=job_card_id,
            assigned_to=user_id,
        )
        await handler.handle_start_operation(cmd)
        await session.commit()
        return {"status": "IN_PRODUCTION"}


@router.post("/{work_order_id}/job-cards/{job_card_id}/pause-operation", status_code=status.HTTP_200_OK)
async def pause_operation(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    request: Request,
    body: Optional[dict] = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Pause a job card operation."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = PauseOperationCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            job_card_id=job_card_id,
            pause_reason=(body or {}).get("pause_reason"),
            operator_notes=(body or {}).get("operator_notes"),
        )
        await handler.handle_pause_operation(cmd)
        await session.commit()
        return {"status": "PAUSED"}


@router.post("/{work_order_id}/job-cards/{job_card_id}/resume-operation", status_code=status.HTTP_200_OK)
async def resume_operation(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    request: Request,
    body: Optional[dict] = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Resume a paused job card operation."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = ResumeOperationCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            job_card_id=job_card_id,
            operator_notes=(body or {}).get("operator_notes"),
        )
        await handler.handle_resume_operation(cmd)
        await session.commit()
        return {"status": "IN_PROGRESS"}


@router.post("/{work_order_id}/job-cards/{job_card_id}/complete-operation", status_code=status.HTTP_200_OK)
async def complete_operation(
    work_order_id: uuid.UUID,
    job_card_id: uuid.UUID,
    request: Request,
    body: Optional[dict] = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Complete a job card operation."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = CompleteOperationCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            job_card_id=job_card_id,
            remarks=(body or {}).get("remarks"),
            operator_notes=(body or {}).get("operator_notes"),
            produced_quantity=Decimal(str((body or {}).get("produced_quantity"))) if (body or {}).get("produced_quantity") is not None else None,
            scrap_quantity=Decimal(str((body or {}).get("scrap_quantity"))) if (body or {}).get("scrap_quantity") is not None else None,
            rework_quantity=Decimal(str((body or {}).get("rework_quantity"))) if (body or {}).get("rework_quantity") is not None else None,
            rejected_quantity=Decimal(str((body or {}).get("rejected_quantity"))) if (body or {}).get("rejected_quantity") is not None else None,
        )
        await handler.handle_complete_operation(cmd)
        await session.commit()
        return {"status": "DONE"}


@router.post("/{work_order_id}/report-wastage", status_code=status.HTTP_200_OK)
async def report_wastage(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Report scrap/wastage during production."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkerHandler(session)
        cmd = ReportWastageCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            scrap_quantity=Decimal(str(body.get("scrap_quantity", 0))),
            recorded_by=user_id,
            notes=body.get("notes"),
        )
        await handler.handle_report_wastage(cmd)
        await session.commit()
        return {"status": "success"}


# ── Phase 5: QC Operational Flow ─────────────────────────────────────────

@router.get("/qc/inspection-queue")
async def get_inspection_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get QC inspection queue for QC dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.quality.services.qc_service import QCService
        service = QCService(session)
        queue = await service.get_inspection_queue(tenant_id=tenant_id)
        return queue


@router.get("/qc/rejected-queue")
async def get_rejected_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get rejected batches for QC dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.quality.services.qc_service import QCService
        service = QCService(session)
        queue = await service.get_rejected_queue(tenant_id=tenant_id)
        return queue


@router.get("/qc/rework-queue")
async def get_rework_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get rework queue for QC dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.quality.services.qc_service import QCService
        service = QCService(session)
        queue = await service.get_rework_queue(tenant_id=tenant_id)
        return queue


@router.post("/{work_order_id}/qc/approve", status_code=status.HTTP_200_OK)
async def qc_approve(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Approve QC inspection."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = QCApproveCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            approved_by=user_id,
            remarks=body.get("remarks"),
        )
        await handler.handle_qc_approve(cmd)
        await session.commit()
        return {"status": "FG_RECEIVED"}


@router.post("/{work_order_id}/qc/reject", status_code=status.HTTP_200_OK)
async def qc_reject(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Reject QC inspection."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = QCRejectCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            rejected_by=user_id,
            reason=body.get("reason", ""),
            send_to_rework=body.get("send_to_rework", False),
        )
        await handler.handle_qc_reject(cmd)
        await session.commit()
        return {"status": "QC_REJECTED"}


@router.post("/{work_order_id}/qc/send-to-rework", status_code=status.HTTP_200_OK)
async def qc_send_to_rework(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Send rejected WO to rework."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = QCSendToReworkCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            sent_by=user_id,
            remarks=body.get("remarks"),
        )
        await handler.handle_qc_send_to_rework(cmd)
        await session.commit()
        return {"status": "REWORK"}


@router.post("/{work_order_id}/fg-receive", status_code=status.HTTP_200_OK)
async def fg_receive(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Receive finished goods after QC approval."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = WorkOrderHandler(session)
        cmd = FGReceiveCommand(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            received_by=user_id,
            remarks=body.get("remarks"),
        )
        await handler.handle_fg_receive(cmd)
        await session.commit()
        return {"status": "FG_RECEIVED"}


@router.get("/{work_order_id}/progress", dependencies=[Depends(require_permission("manufacturing:read"))])
async def get_work_order_progress(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        wo = (
            await session.execute(
                select(WorkOrderModel).where(
                    WorkOrderModel.id == work_order_id,
                    WorkOrderModel.tenant_id == tenant_id,
                    WorkOrderModel.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not wo:
            return JSONResponse(status_code=404, content={"message": "Work order not found"})

        jc_rows = (
            await session.execute(
                select(JobCardModel).where(JobCardModel.work_order_id == work_order_id).order_by(JobCardModel.sequence)
            )
        ).scalars().all()

        planned = float(wo.planned_quantity or 0)
        produced = float(wo.produced_quantity or 0)
        pct = (produced / planned * 100) if planned > 0 else 0.0
        operations = []
        for jc in jc_rows:
            dur = None
            if jc.started_at and jc.completed_at:
                started_at = jc.started_at
                completed_at = jc.completed_at
                if started_at.tzinfo is None and completed_at.tzinfo is not None:
                    completed_at = completed_at.replace(tzinfo=None)
                elif started_at.tzinfo is not None and completed_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=None)
                dur = max(0.0, (completed_at - started_at).total_seconds())
                dur -= float(Decimal(str(jc.total_downtime_seconds or 0)))
            jc_produced = Decimal(str(jc.produced_quantity or 0))
            jc_scrap = Decimal(str(jc.scrap_quantity or 0))
            jc_rejected = Decimal(str(jc.rejected_quantity or 0))
            output_qty = jc_produced + jc_scrap + jc_rejected
            yield_percent = float((jc_produced / output_qty) * Decimal("100")) if output_qty > 0 else 0.0
            progress_percent = (
                100.0 if jc.status in ("DONE", "COMPLETED")
                else 90.0 if jc.status == "QC_PENDING"
                else 50.0 if jc.status == "IN_PROGRESS"
                else 40.0 if jc.status == "PAUSED"
                else 0.0
            )
            operations.append({
                "job_card_id": str(jc.id),
                "operation_id": str(jc.operation_id),
                "operation_name": jc.operation.name if jc.operation else None,
                "sequence": jc.sequence,
                "status": jc.status,
                "started_at": jc.started_at.isoformat() if jc.started_at else None,
                "paused_at": jc.paused_at.isoformat() if jc.paused_at else None,
                "completed_at": jc.completed_at.isoformat() if jc.completed_at else None,
                "total_downtime_seconds": float(Decimal(str(jc.total_downtime_seconds or 0))),
                "actual_duration_seconds": dur,
                "produced_quantity": float(jc_produced),
                "scrap_quantity": float(jc_scrap),
                "rework_quantity": float(Decimal(str(jc.rework_quantity or 0))),
                "rejected_quantity": float(jc_rejected),
                "yield_percent": round(yield_percent, 2),
                "percent": progress_percent,
                "pause_reason": jc.pause_reason,
            })

        done_ops = sum(1 for o in operations if o["status"] == "DONE")
        op_pct = (done_ops / len(operations) * 100) if operations else pct

        return {
            "work_order_id": str(wo.id),
            "wo_number": wo.wo_number,
            "status": wo.status,
            "percent_complete": round(pct, 2),
            "operation_percent_complete": round(op_pct, 2),
            "planned_quantity": planned,
            "produced_quantity": produced,
            "remaining_quantity": max(0.0, planned - produced),
            "scrap_quantity": float(wo.scrap_quantity or 0),
            "yield_percent": round(
                (produced / (produced + float(wo.scrap_quantity or 0)) * 100)
                if (produced + float(wo.scrap_quantity or 0)) > 0
                else 0.0,
                2,
            ),
            "scrap_percent": round(
                (float(wo.scrap_quantity or 0) / (produced + float(wo.scrap_quantity or 0)) * 100)
                if (produced + float(wo.scrap_quantity or 0)) > 0
                else 0.0,
                2,
            ),
            "operations": operations,
        }


@router.get("/{work_order_id}/material-variance", dependencies=[Depends(require_permission("manufacturing:read"))])
async def get_material_variance(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    from backend.app.infrastructure.persistence.models.material_consumption_model import (
        MaterialConsumptionRecordModel,
    )

    container = get_container(request)
    async with container.session_factory() as session:
        rows = (
            await session.execute(
                select(MaterialConsumptionRecordModel).where(
                    MaterialConsumptionRecordModel.tenant_id == tenant_id,
                    MaterialConsumptionRecordModel.work_order_id == work_order_id,
                ).order_by(MaterialConsumptionRecordModel.recorded_at.desc())
            )
        ).scalars().all()
        return [
            {
                "material_id": str(r.material_id),
                "planned_quantity": r.planned_quantity,
                "actual_quantity": r.actual_quantity,
                "variance_quantity": r.variance_quantity,
                "scrap_quantity": r.scrap_quantity,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in rows
        ]


@router.get("/{work_order_id}/reservations", dependencies=[Depends(require_permission("manufacturing:read"))])
async def get_work_order_reservations(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    from backend.app.application.inventory.services.inventory_reservation_service import (
        InventoryReservationService,
    )

    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryReservationService(session)
        rows = await service.get_reservation_audit_trail(
            tenant_id=tenant_id,
            reference_type="work_order",
            reference_id=work_order_id,
        )
        return [
            {
                "id": str(r.id),
                "material_id": str(r.material_id),
                "quantity": float(r.quantity),
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "issued_quantity": float(r.issued_quantity),
                "consumed_quantity": float(r.consumed_quantity),
                "returned_quantity": float(r.returned_quantity),
                "batch_id": str(r.batch_id) if r.batch_id else None,
            }
            for r in rows
        ]


@router.post("/{work_order_id}/pick-list", dependencies=[Depends(require_permission("inventory:write"))])
async def generate_pick_list(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    from backend.app.application.inventory.services.pick_list_service import PickListService

    container = get_container(request)
    async with container.session_factory() as session:
        service = PickListService(session)
        result = await service.generate_from_wo(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            created_by=user_id,
        )
        await session.commit()
        return result


# ── Production Hold / Resume (Req 26.1, 26.2) ──────────────────────────────


@router.post(
    "/{work_order_id}/hold",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def put_work_order_on_hold(
    work_order_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Put a work order on production hold with a reason.

    Only valid when the WO is IN_PRODUCTION. Transitions the WO to
    PRODUCTION_HOLD, records hold_reason and hold_started_at, creates
    an audit log entry, and triggers a machine_breakdown notification.

    Requirements: 26.1, 26.2
    """
    from datetime import datetime, timezone as tz
    from sqlalchemy import select, and_

    reason = (body or {}).get("reason", "")
    if not reason or not reason.strip():
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error_code": "VALIDATION_ERROR", "message": "Hold reason is required", "validation_errors": []},
        )

    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        wo = (await session.execute(stmt)).scalar_one_or_none()
        if not wo:
            return JSONResponse(
                status_code=404,
                content={"error_code": "NOT_FOUND", "message": "Work Order not found", "validation_errors": []},
            )

        if wo.status != "IN_PRODUCTION":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error_code": "INVALID_STATUS_TRANSITION",
                    "message": f"Cannot hold work order in status '{wo.status}'. Must be IN_PRODUCTION.",
                    "validation_errors": [],
                },
            )

        before_status = wo.status
        wo.status = "PRODUCTION_HOLD"
        wo.hold_reason = reason.strip()
        wo.hold_started_at = datetime.now(tz.utc)
        wo.updated_at = datetime.now(tz.utc)
        await session.flush()

        # Audit log
        try:
            from backend.app.services.audit_log_service import AuditLogService
            audit_service = AuditLogService(session)
            await audit_service.log_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action_type="production_hold",
                entity_type="work_order",
                entity_id=work_order_id,
                before_state={"status": before_status},
                after_state={"status": wo.status, "hold_reason": wo.hold_reason},
                reason=reason.strip(),
            )
        except Exception:
            pass

        # Notification
        try:
            from backend.app.application.notifications.notification_service import NotificationService
            notif_service = NotificationService(session)
            await notif_service.create_notification(
                tenant_id=tenant_id,
                notification_type="machine_breakdown",
                title=f"Production Hold - WO {wo.wo_number}",
                message=f"Work Order {wo.wo_number} placed on hold. Reason: {reason.strip()}",
                reference_id=str(work_order_id),
                reference_type="work_order",
            )
        except Exception:
            pass

        await session.commit()
        return {
            "status": wo.status,
            "hold_reason": wo.hold_reason,
            "hold_started_at": wo.hold_started_at.isoformat() if wo.hold_started_at else None,
        }


@router.post(
    "/{work_order_id}/resume",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def resume_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    body: Optional[dict] = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Resume a work order from production hold.

    Only valid when the WO is in PRODUCTION_HOLD status. Transitions the
    WO back to IN_PRODUCTION and clears hold fields.

    Requirements: 26.2
    """
    from datetime import datetime, timezone as tz
    from sqlalchemy import select, and_

    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.id == work_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        wo = (await session.execute(stmt)).scalar_one_or_none()
        if not wo:
            return JSONResponse(
                status_code=404,
                content={"error_code": "NOT_FOUND", "message": "Work Order not found", "validation_errors": []},
            )

        if wo.status != "PRODUCTION_HOLD":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error_code": "INVALID_STATUS_TRANSITION",
                    "message": f"Cannot resume work order in status '{wo.status}'. Must be PRODUCTION_HOLD.",
                    "validation_errors": [],
                },
            )

        before_status = wo.status
        hold_duration_seconds = None
        if wo.hold_started_at:
            now = datetime.now(tz.utc)
            hold_start = wo.hold_started_at
            if hold_start.tzinfo is None:
                from datetime import timezone as _tz
                hold_start = hold_start.replace(tzinfo=_tz.utc)
            hold_duration_seconds = (now - hold_start).total_seconds()

        wo.status = "IN_PRODUCTION"
        wo.hold_reason = None
        wo.hold_started_at = None
        wo.updated_at = datetime.now(tz.utc)
        await session.flush()

        # Audit log
        try:
            from backend.app.services.audit_log_service import AuditLogService
            audit_service = AuditLogService(session)
            await audit_service.log_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action_type="production_resume",
                entity_type="work_order",
                entity_id=work_order_id,
                before_state={"status": before_status},
                after_state={"status": wo.status},
                reason=(body or {}).get("notes"),
                metadata={"hold_duration_seconds": hold_duration_seconds},
            )
        except Exception:
            pass

        await session.commit()
        return {
            "status": wo.status,
            "hold_duration_seconds": hold_duration_seconds,
        }


