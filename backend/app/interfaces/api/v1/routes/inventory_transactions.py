"""Inventory Transaction and Procurement API endpoints.

Provides:
- GET /inventory/transactions — paginated with filters (material_id, type, date range, reference)
- GET /inventory/transactions/{material_id}/balance — running balance for material
- GET /inventory/materials/{id}/reconciliation — reconciliation status check
- GET /procurement/dashboard — procurement pipeline summary

Requirements: 30.1–30.8, 31.3, 31.4, 31.8, 31.9
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.services.inventory_transaction_service import InventoryTransactionService
from backend.app.services.kpi_query_service import KPIQueryService


# ── Response Schemas ────────────────────────────────────────────────────────────


class TransactionItemResponse(BaseModel):
    """Single inventory transaction."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    transaction_type: str
    quantity: float
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    timestamp: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedTransactionsResponse(BaseModel):
    """Paginated transaction list response."""

    items: List[TransactionItemResponse]
    total: int
    offset: int
    limit: int


class RunningBalanceEntryResponse(BaseModel):
    """Transaction with cumulative running balance."""

    id: uuid.UUID
    material_id: uuid.UUID
    transaction_type: str
    quantity: float
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    timestamp: datetime
    notes: Optional[str] = None
    running_balance: float


class ReconciliationResponse(BaseModel):
    """Reconciliation status for a material."""

    material_id: uuid.UUID
    transaction_sum: float
    current_stock: float
    difference: float
    is_reconciled: bool
    tolerance: float


class ProcurementDashboardResponse(BaseModel):
    """Procurement pipeline summary."""

    pending_requisitions: int
    approved_requisitions: int
    pending_purchase_orders: int
    supplier_deliveries_next_7_days: int
    overdue_deliveries: int
    grn_pending: int
    material_shortages: int


# ── Routers ─────────────────────────────────────────────────────────────────────

inventory_transactions_router = APIRouter(
    prefix="/inventory", tags=["Inventory Transactions"]
)
procurement_router = APIRouter(prefix="/procurement", tags=["Procurement"])


# ── Inventory Transaction Endpoints ────────────────────────────────────────────


@inventory_transactions_router.get(
    "/transactions/history",
    response_model=PaginatedTransactionsResponse,
    summary="List inventory transactions with filters",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def get_inventory_transactions(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    material_id: Optional[uuid.UUID] = Query(None, description="Filter by material ID"),
    transaction_type: Optional[str] = Query(
        None, alias="type", description="Filter by transaction type (e.g. FG_RECEIPT, DISPATCH)"
    ),
    date_from: Optional[datetime] = Query(None, description="Filter from date (inclusive)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (inclusive)"),
    reference_type: Optional[str] = Query(
        None, description="Filter by reference type (e.g. work_order, sales_order)"
    ),
    reference_id: Optional[uuid.UUID] = Query(None, description="Filter by reference ID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Page size (max 200)"),
):
    """Retrieve paginated inventory transactions with optional filters.

    Supports filtering by material, transaction type, date range, and reference.
    Results are ordered by timestamp descending (most recent first).
    """
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTransactionService(session)
        result = await service.get_transactions(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            date_from=date_from,
            date_to=date_to,
            reference_type=reference_type,
            reference_id=reference_id,
            offset=offset,
            limit=limit,
        )

    items = [
        TransactionItemResponse(
            id=record.id,
            tenant_id=record.tenant_id,
            material_id=record.material_id,
            transaction_type=record.transaction_type,
            quantity=float(record.quantity),
            reference_type=record.reference_type,
            reference_id=record.reference_id,
            warehouse_id=record.warehouse_id,
            batch_id=record.batch_id,
            user_id=record.user_id,
            timestamp=record.timestamp,
            notes=record.notes,
        )
        for record in result.items
    ]

    return PaginatedTransactionsResponse(
        items=items,
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@inventory_transactions_router.get(
    "/transactions/{material_id}/balance",
    response_model=List[RunningBalanceEntryResponse],
    summary="Get running balance for a material",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def get_running_balance(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Compute and return the cumulative running balance for a material.

    Returns all transactions for the material ordered by timestamp ascending,
    with a running_balance field showing the cumulative sum at each point.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTransactionService(session)
        entries = await service.get_running_balance(
            tenant_id=tenant_id,
            material_id=material_id,
        )

    return [
        RunningBalanceEntryResponse(
            id=entry.transaction.id,
            material_id=entry.transaction.material_id,
            transaction_type=entry.transaction.transaction_type,
            quantity=float(entry.transaction.quantity),
            reference_type=entry.transaction.reference_type,
            reference_id=entry.transaction.reference_id,
            warehouse_id=entry.transaction.warehouse_id,
            user_id=entry.transaction.user_id,
            timestamp=entry.transaction.timestamp,
            notes=entry.transaction.notes,
            running_balance=float(entry.running_balance),
        )
        for entry in entries
    ]


@inventory_transactions_router.get(
    "/materials/{material_id}/reconciliation",
    response_model=ReconciliationResponse,
    summary="Check reconciliation status for a material",
    dependencies=[Depends(require_permission("inventory:read"))],
)
async def check_reconciliation(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Compare sum of all transactions for a material against its current_stock.

    Returns whether the material is reconciled (difference within tolerance of 0.001).
    """
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTransactionService(session)
        try:
            result = await service.check_reconciliation(
                tenant_id=tenant_id,
                material_id=material_id,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    return ReconciliationResponse(
        material_id=result.material_id,
        transaction_sum=float(result.transaction_sum),
        current_stock=float(result.current_stock),
        difference=float(result.difference),
        is_reconciled=result.is_reconciled,
        tolerance=float(result.tolerance),
    )


# ── Procurement Dashboard Endpoint ─────────────────────────────────────────────


@procurement_router.get(
    "/dashboard",
    response_model=ProcurementDashboardResponse,
    summary="Procurement pipeline summary",
    dependencies=[Depends(require_permission("procurement:read"))],
)
async def get_procurement_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Return procurement pipeline summary.

    Includes: pending requisitions, approved requisitions, pending POs,
    supplier deliveries due in 7 days, overdue deliveries, GRN pending,
    and material shortages blocking work orders.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        service = KPIQueryService(session)
        result = await service.get_procurement_summary(tenant_id=tenant_id)

    return ProcurementDashboardResponse(
        pending_requisitions=result.pending_requisitions,
        approved_requisitions=result.approved_requisitions,
        pending_purchase_orders=result.pending_purchase_orders,
        supplier_deliveries_next_7_days=result.supplier_deliveries_next_7_days,
        overdue_deliveries=result.overdue_deliveries,
        grn_pending=result.grn_pending,
        material_shortages=result.material_shortages,
    )
