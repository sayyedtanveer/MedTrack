"""Capacity Planning & MRP REST API endpoints.

Routes:
  GET  /api/v1/capacity/load-chart?start=date&end=date
  GET  /api/v1/capacity/bottlenecks?threshold=90
  POST /api/v1/capacity/schedule          ← list (GET-style via POST with body filter)
  PATCH /api/v1/capacity/schedule/{wo_id} ← drag-drop reschedule

  POST /api/v1/mrp/run
  GET  /api/v1/mrp/suggestions
  POST /api/v1/mrp/suggestions/{id}/approve
  POST /api/v1/mrp/suggestions/{id}/reject
  POST /api/v1/mrp/suggestions/bulk-approve
  POST /api/v1/mrp/suggestions/convert-to-po
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.manufacturing.services.capacity_service import CapacityService
from backend.app.application.supply_chain.mrp_service import MRPService

router = APIRouter(tags=["Capacity & MRP"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────── #


class RescheduleRequest(BaseModel):
    work_order_id: uuid.UUID
    new_start: date
    new_due: date
    direction: Optional[str] = Field(default="forward", description="'forward' or 'backward'")


class BulkApproveRequest(BaseModel):
    suggestion_ids: List[str]


class ConvertToPORequest(BaseModel):
    suggestion_ids: Optional[List[str]] = None


class ScheduleFilterRequest(BaseModel):
    start: Optional[date] = None
    end: Optional[date] = None


# ── Capacity endpoints ────────────────────────────────────────────────────── #


@router.get("/capacity/load-chart")
async def load_chart(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    start: Optional[date] = Query(default=None, description="ISO date, e.g. 2025-01-01"),
    end: Optional[date] = Query(default=None, description="ISO date, e.g. 2025-01-31"),
):
    """Workstation load percentages for the given date range.

    Colour semantics:  status='ok' (<70%), 'warning' (70–90%), 'critical' (>90%)
    """
    from datetime import date as _date, timedelta

    today = _date.today()
    start = start or today
    end = end or (today + timedelta(days=29))

    container = get_container(request)
    async with container.session_factory() as session:
        svc = CapacityService(session)
        data = await svc.get_load_chart(tenant_id, start, end)
    return data


@router.get("/capacity/bottlenecks")
async def bottlenecks(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    threshold: float = Query(default=90.0, ge=0, le=200),
):
    """Workstations exceeding the load threshold (default 90%).

    Each entry includes a plain-English suggestion (overtime / reallocation).
    """
    container = get_container(request)
    async with container.session_factory() as session:
        svc = CapacityService(session)
        data = await svc.get_bottlenecks(tenant_id, threshold)
    return data


@router.get("/capacity/schedule")
async def get_schedule(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    start: Optional[date] = Query(default=None),
    end: Optional[date] = Query(default=None),
):
    """Gantt-compatible list of work orders with start/due dates and progress %."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = CapacityService(session)
        data = await svc.get_schedule(tenant_id, start, end)
    return data


@router.post("/capacity/schedule", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("procurement:write"))])
async def reschedule_work_order(
    body: RescheduleRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Drag-drop reschedule — update start & due dates of a work order."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = CapacityService(session)
        try:
            result = await svc.reschedule(
                tenant_id,
                body.work_order_id,
                body.new_start,
                body.new_due,
            )
            await session.commit()
        except ValueError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"error": str(exc)},
            )
    return result


# ── MRP endpoints ─────────────────────────────────────────────────────────── #


@router.post("/mrp/run", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("procurement:write"))])
async def run_mrp(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Execute a full MRP run for this tenant.

    Calculates net requirements from WOs, safety stock, and current inventory,
    then generates purchase suggestions grouped by supplier.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        svc = MRPService(session)
        result = await svc.run(tenant_id)
    return result


@router.get("/mrp/suggestions")
async def list_suggestions(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    status_filter: Optional[str] = Query(default=None, alias="status"),
):
    """List all MRP purchase suggestions for the tenant.

    Filter by status: pending | approved | rejected | converted
    """
    container = get_container(request)
    async with container.session_factory() as session:
        svc = MRPService(session)
        suggestions = await svc.get_suggestions(tenant_id, status_filter=status_filter)
    return suggestions


@router.post("/mrp/suggestions/{suggestion_id}/approve", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("procurement:write"))])
async def approve_suggestion(
    suggestion_id: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Approve a single MRP purchase suggestion."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = MRPService(session)
        try:
            result = await svc.approve_suggestion(tenant_id, suggestion_id)
        except ValueError as exc:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": str(exc)},
            )
    return result


@router.post("/mrp/suggestions/{suggestion_id}/reject", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("procurement:write"))])
async def reject_suggestion(
    suggestion_id: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Reject a single MRP purchase suggestion."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = MRPService(session)
        try:
            result = await svc.reject_suggestion(tenant_id, suggestion_id)
        except ValueError as exc:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": str(exc)},
            )
    return result


@router.post("/mrp/suggestions/bulk-approve", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("procurement:write"))])
async def bulk_approve(
    body: BulkApproveRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Bulk-approve a list of MRP suggestions by ID."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = MRPService(session)
        result = await svc.bulk_approve(tenant_id, body.suggestion_ids)
    return result


@router.post("/mrp/suggestions/convert-to-po", status_code=status.HTTP_200_OK, dependencies=[Depends(require_permission("procurement:write"))])
async def convert_to_po(
    body: ConvertToPORequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Convert approved suggestions to draft Purchase Orders (batched by supplier).

    Pass suggestion_ids to convert specific items, or omit to convert all approved.
    Returns a list of created PO references.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        svc = MRPService(session)
        try:
            pos = await svc.convert_to_po(
                tenant_id,
                suggestion_ids=body.suggestion_ids,
                created_by=user_id,
            )
        except Exception as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": str(exc)},
            )
    return {"purchase_orders": pos}
