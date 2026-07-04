"""Workflow Orchestration REST API endpoints.

Provides endpoints for end-to-end workflow management across modules.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)
from backend.app.application.sales.partial_fulfillment_service import (
    PartialFulfillmentService,
)

router = APIRouter(prefix="/workflow", tags=["Workflow Orchestration"])


async def _get_db_session(request):
    """Get database session from request."""
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


@router.post(
    "/sales-orders/{sales_order_id}/approve-workflow",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("sales:approve_order"))],
)
async def approve_sales_order_workflow(
    sales_order_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Approve Sales Order and trigger workflow.
    
    Transition: APPROVED → WORK_ORDER_CREATED
    Action: Create Work Orders for each line item
    """
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
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Complete Work Order and trigger workflow.
    
    Transition: FG_RECEIVED → READY_FOR_DISPATCH
    Action: Update linked Sales Order to READY_FOR_DISPATCH
    """
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
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    approved_by: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Approve QC and trigger workflow.
    
    Transition: QC_APPROVED → FG_RECEIVED
    Action: Automatically increase FG stock
    """
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
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Mark Order as delivered and trigger invoicing.
    
    Transition: DELIVERED → INVOICED
    Action: Trigger invoice creation
    """
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
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Record payment and complete workflow.
    
    Transition: INVOICED → PAYMENT_RECEIVED → COMPLETED
    Action: Update Sales Order status
    """
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
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Get complete workflow status for a Sales Order.
    
    Returns status across all stages:
    - Sales Order status
    - Work Order status
    - Material reservation status
    - QC status
    - Delivery status
    - Invoice status
    - Payment status
    - Estimated dates (Req 28.8)
    - Allocated quantities per line
    """
    service = WorkflowOrchestrationService(session)
    result = await service.get_workflow_status(
        tenant_id=tenant_id,
        sales_order_id=sales_order_id,
    )

    # Extend with estimated dates and allocated quantities (Req 28.8)
    from sqlalchemy import select, and_
    from backend.app.infrastructure.persistence.models.sales_models import (
        SalesOrderModel, SalesOrderLineModel,
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
            so.estimated_completion_date.isoformat() if so.estimated_completion_date else None
        )
        result["expected_dispatch_date"] = (
            so.expected_dispatch_date.isoformat() if so.expected_dispatch_date else None
        )
        result["expected_delivery_date"] = (
            so.expected_delivery_date.isoformat() if so.expected_delivery_date else None
        )
        result["delivery_date"] = so.delivery_date

        # Add per-line allocated/dispatched quantities
        result["lines"] = [
            {
                "line_id": str(line.id),
                "product_id": str(line.product_id),
                "quantity": float(line.quantity),
                "allocated_quantity": float(line.allocated_quantity),
                "dispatched_quantity": float(line.dispatched_quantity),
                "line_status": line.line_status,
            }
            for line in (so.lines or [])
        ]

    return result


@router.get(
    "/sales-orders/{sales_order_id}/tracking",
    dependencies=[Depends(require_permission("sales:read"))],
)
async def get_order_tracking(
    sales_order_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Get order tracking with estimated dates.

    Returns current stage, estimated completion date, expected dispatch
    date, and expected delivery date. The dates are calculated from
    linked work order due dates and configurable lead times.

    Requirements: 28.1–28.7
    """
    from sqlalchemy import select, and_
    from datetime import date as date_type, timedelta
    from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel
    from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel

    so_stmt = select(SalesOrderModel).where(
        and_(
            SalesOrderModel.id == sales_order_id,
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.is_deleted.is_(False),
        )
    )
    so = (await session.execute(so_stmt)).scalar_one_or_none()
    if not so:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Sales Order {sales_order_id} not found")

    # Get linked work orders
    wo_stmt = select(WorkOrderModel).where(
        and_(
            WorkOrderModel.sales_order_id == sales_order_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
    )
    work_orders = (await session.execute(wo_stmt)).scalars().all()

    # Calculate estimated completion date (Req 28.2)
    # = max(due_date) among incomplete WOs
    completed_statuses = {"FG_RECEIVED", "COMPLETED", "CLOSED", "CANCELLED", "REJECTED"}
    incomplete_wos = [
        wo for wo in work_orders if wo.status not in completed_statuses
    ]

    estimated_completion: date_type | None = None
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
        # No linked WOs (stock-available path) — Req 28.6
        estimated_completion = date_type.today()

    # Use persisted dates if available and no recalculation needed
    if estimated_completion is None and so.estimated_completion_date:
        estimated_completion = so.estimated_completion_date

    # Lead times (defaults per Req 28.3, 28.4)
    dispatch_lead_days = 1
    delivery_lead_days = 3

    expected_dispatch: date_type | None = None
    expected_delivery: date_type | None = None

    if estimated_completion:
        expected_dispatch = estimated_completion + timedelta(days=dispatch_lead_days)
        expected_delivery = expected_dispatch + timedelta(days=delivery_lead_days)

    # Use persisted dates as fallback
    if expected_dispatch is None and so.expected_dispatch_date:
        expected_dispatch = so.expected_dispatch_date
    if expected_delivery is None and so.expected_delivery_date:
        expected_delivery = so.expected_delivery_date

    # Check if delivery date is at risk (Req 28.7)
    customer_promise_date = so.delivery_date
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

    # Determine current stage from SO status
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
    pass  # No additional fields needed — line_id is in the path


class ShortCloseLineRequest(BaseModel):
    """Request body for short-closing a SO line."""
    pass  # No additional fields needed — line_id is in the path


@router.post(
    "/sales-order-lines/{line_id}/create-wo-for-remaining",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def create_wo_for_remaining(
    line_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Create a new Work Order for the remaining unfulfilled quantity of a PARTIAL SO line.

    Req 19.5: Creates a new WO with planned_quantity = ordered_quantity - allocated_quantity,
    linked to the same sales order and product.
    """
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
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        await session.rollback()
        raise


@router.post(
    "/sales-order-lines/{line_id}/short-close",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def short_close_line(
    line_id: uuid.UUID,
    request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    """
    Short-close a PARTIAL SO line.

    Req 19.6: Updates line status to SHORT_CLOSED, reduces ordered_quantity to
    allocated_quantity, and recalculates the sales order totals.
    """
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
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        await session.rollback()
        raise
