"""Workflow Orchestration REST API endpoints.

Provides endpoints for end-to-end workflow management across modules.
All endpoints use get_container(request) + session_factory() for DB access,
which is the established pattern throughout this codebase and avoids the
FastAPI query-parameter injection bug that occurs when a custom dependency
function takes `request: Request` as a plain parameter.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_user_id,
    get_container,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)
from backend.app.application.sales.partial_fulfillment_service import (
    PartialFulfillmentService,
)

router = APIRouter(prefix="/workflow", tags=["Workflow Orchestration"])


# ──────────────────────────── Sales Order Workflow ────────────────────────────


@router.post(
    "/sales-orders/{sales_order_id}/approve-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("sales:approve_order"))],
)
async def approve_sales_order_workflow(
    sales_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Approve Sales Order and trigger workflow (APPROVED → WORK_ORDER_CREATED)."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = WorkflowOrchestrationService(session)
        result = await service.on_sales_order_approved(
            tenant_id=tenant_id,
            sales_order_id=sales_order_id,
        )
        await session.commit()
    return result


@router.post(
    "/work-orders/{work_order_id}/complete-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("manufacturing:write"))],
)
async def complete_work_order_workflow(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Complete Work Order and update linked SO to READY_FOR_DISPATCH."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = WorkflowOrchestrationService(session)
        result = await service.on_work_order_completed(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
        )
        await session.commit()
    return result


@router.post(
    "/work-orders/{work_order_id}/qc-approve-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("quality:write"))],
)
async def qc_approve_workflow(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    approved_by: uuid.UUID = Depends(get_current_user_id),
):
    """Approve QC and trigger FG stock increase (QC_APPROVED → FG_RECEIVED)."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = WorkflowOrchestrationService(session)
        result = await service.on_qc_approved(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
            received_by=approved_by,
        )
        await session.commit()
    return result


@router.post(
    "/sales-orders/{sales_order_id}/deliver-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def deliver_order_workflow(
    sales_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Mark Order as delivered and trigger invoicing (DELIVERED → INVOICED)."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = WorkflowOrchestrationService(session)
        result = await service.on_order_delivered(
            tenant_id=tenant_id,
            sales_order_id=sales_order_id,
        )
        await session.commit()
    return result


@router.post(
    "/sales-orders/{sales_order_id}/payment-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("finance:write"))],
)
async def receive_payment_workflow(
    sales_order_id: uuid.UUID,
    payment_amount: Decimal,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Record payment and complete workflow (INVOICED → PAYMENT_RECEIVED → COMPLETED)."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = WorkflowOrchestrationService(session)
        result = await service.on_payment_received(
            tenant_id=tenant_id,
            sales_order_id=sales_order_id,
            payment_amount=payment_amount,
        )
        await session.commit()
    return result


@router.get(
    "/sales-orders/{sales_order_id}/status",
    dependencies=[Depends(require_permission("sales:read"))],
)
async def get_workflow_status(
    sales_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get complete workflow status for a Sales Order across all lifecycle stages."""
    from sqlalchemy import select, and_
    from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel

    container = get_container(request)
    async with container.session_factory() as session:
        service = WorkflowOrchestrationService(session)
        result = await service.get_workflow_status(
            tenant_id=tenant_id,
            sales_order_id=sales_order_id,
        )

        stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        so = (await session.execute(stmt)).scalar_one_or_none()

        if so:
            result["estimated_completion_date"] = (
                so.estimated_completion_date.isoformat()
                if getattr(so, "estimated_completion_date", None)
                else None
            )
            result["expected_dispatch_date"] = (
                so.expected_dispatch_date.isoformat()
                if getattr(so, "expected_dispatch_date", None)
                else None
            )
            result["expected_delivery_date"] = (
                so.expected_delivery_date.isoformat()
                if getattr(so, "expected_delivery_date", None)
                else None
            )
            result["delivery_date"] = getattr(so, "delivery_date", None)

            lines = getattr(so, "lines", None) or []
            result["lines"] = [
                {
                    "line_id": str(line.id),
                    "product_id": str(line.product_id),
                    "quantity": float(line.quantity),
                    "allocated_quantity": float(getattr(line, "allocated_quantity", 0) or 0),
                    "dispatched_quantity": float(getattr(line, "dispatched_quantity", 0) or 0),
                    "line_status": getattr(line, "line_status", None),
                }
                for line in lines
            ]

    return result


@router.get(
    "/sales-orders/{sales_order_id}/tracking",
    dependencies=[Depends(require_permission("sales:read"))],
)
async def get_order_tracking(
    sales_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get order tracking with estimated dates (Req 28.1–28.7)."""
    from sqlalchemy import select, and_
    from datetime import date as date_type, timedelta
    from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
    from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel

    container = get_container(request)
    async with container.session_factory() as session:
        so_stmt = select(SalesOrderModel).where(
            and_(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        so = (await session.execute(so_stmt)).scalar_one_or_none()
        if not so:
            raise HTTPException(status_code=404, detail=f"Sales Order {sales_order_id} not found")

        wo_stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.sales_order_id == sales_order_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        work_orders = (await session.execute(wo_stmt)).scalars().all()

        completed_statuses = {"FG_RECEIVED", "COMPLETED", "CLOSED", "CANCELLED", "REJECTED"}
        incomplete_wos = [wo for wo in work_orders if wo.status not in completed_statuses]

        estimated_completion: Optional[date_type] = None
        if incomplete_wos:
            due_dates = []
            for wo in incomplete_wos:
                if wo.due_date:
                    if isinstance(wo.due_date, str):
                        try:
                            due_dates.append(date_type.fromisoformat(wo.due_date))
                        except (ValueError, TypeError):
                            pass
                    else:
                        due_dates.append(wo.due_date)
            if due_dates:
                estimated_completion = max(due_dates)
        elif not work_orders:
            estimated_completion = date_type.today()

        if estimated_completion is None:
            ec = getattr(so, "estimated_completion_date", None)
            if ec:
                estimated_completion = ec

        dispatch_lead_days = 1
        delivery_lead_days = 3
        expected_dispatch: Optional[date_type] = None
        expected_delivery: Optional[date_type] = None

        if estimated_completion:
            expected_dispatch = estimated_completion + timedelta(days=dispatch_lead_days)
            expected_delivery = expected_dispatch + timedelta(days=delivery_lead_days)

        if expected_dispatch is None:
            ed = getattr(so, "expected_dispatch_date", None)
            if ed:
                expected_dispatch = ed
        if expected_delivery is None:
            edv = getattr(so, "expected_delivery_date", None)
            if edv:
                expected_delivery = edv

        customer_promise_date = getattr(so, "delivery_date", None)
        at_risk = False
        if expected_delivery and customer_promise_date:
            try:
                promise = (
                    date_type.fromisoformat(customer_promise_date)
                    if isinstance(customer_promise_date, str)
                    else customer_promise_date
                )
                at_risk = expected_delivery > promise
            except (ValueError, TypeError):
                pass

        service = WorkflowOrchestrationService(session)
        current_stage = service._determine_workflow_stage(so.status, work_orders)

    return {
        "sales_order_id": str(sales_order_id),
        "order_number": so.order_number,
        "status": so.status,
        "current_stage": current_stage,
        "estimated_completion_date": estimated_completion.isoformat() if estimated_completion else None,
        "expected_dispatch_date": expected_dispatch.isoformat() if expected_dispatch else None,
        "expected_delivery_date": expected_delivery.isoformat() if expected_delivery else None,
        "customer_promise_date": customer_promise_date,
        "delivery_at_risk": at_risk,
        "work_orders": [
            {
                "wo_id": str(wo.id),
                "wo_number": wo.wo_number,
                "status": wo.status,
                "due_date": (
                    wo.due_date.isoformat()
                    if wo.due_date and not isinstance(wo.due_date, str)
                    else wo.due_date
                ),
                "produced_quantity": float(wo.produced_quantity),
                "planned_quantity": float(wo.planned_quantity),
            }
            for wo in work_orders
        ],
    }


# ──────────────────────────── Partial Fulfillment Endpoints ────────────────────────────


class CreateWOForRemainingRequest(BaseModel):
    """Request body for creating a new WO for remaining SO line quantity."""
    pass


class ShortCloseLineRequest(BaseModel):
    """Request body for short-closing a SO line."""
    pass


@router.post(
    "/sales-order-lines/{line_id}/create-wo-for-remaining",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def create_wo_for_remaining(
    line_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create a new WO for the remaining unfulfilled quantity of a PARTIAL SO line (Req 19.5)."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = PartialFulfillmentService(session)
        try:
            result = await service.create_wo_for_remaining(
                tenant_id=tenant_id,
                sales_order_line_id=line_id,
                created_by=user_id,
            )
            await session.commit()
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/sales-order-lines/{line_id}/short-close",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def short_close_line(
    line_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Short-close a PARTIAL SO line (Req 19.6)."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = PartialFulfillmentService(session)
        try:
            result = await service.short_close_line(
                tenant_id=tenant_id,
                sales_order_line_id=line_id,
                closed_by=user_id,
            )
            await session.commit()
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
