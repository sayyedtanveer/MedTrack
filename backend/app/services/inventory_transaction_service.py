"""
InventoryTransactionService — query service for inventory transaction history.

Provides:
  - Full transaction type coverage for all stock movements
  - Paginated, filterable transaction retrieval
  - Running balance computation (cumulative sum per material)
  - Stock reconciliation check (sum of transactions vs current_stock)

Requirements: 31.1, 31.2, 31.5, 31.6, 31.7, 31.9, 31.10
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)
from backend.app.infrastructure.persistence.models.material_model import MaterialModel


# ---------------------------------------------------------------------------
# Transaction Types — complete set for all stock movements (Requirement 31.1)
# ---------------------------------------------------------------------------


class InventoryTransactionType(str, Enum):
    """All valid transaction types for inventory movements."""

    OPENING_STOCK = "OPENING_STOCK"
    PURCHASE_RECEIPT = "PURCHASE_RECEIPT"
    RESERVATION = "RESERVATION"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"
    MATERIAL_ISSUE = "MATERIAL_ISSUE"
    PRODUCTION_CONSUMPTION = "PRODUCTION_CONSUMPTION"
    FG_RECEIPT = "FG_RECEIPT"
    DISPATCH = "DISPATCH"
    DISPATCH_REVERSAL = "DISPATCH_REVERSAL"
    SALES_RETURN = "SALES_RETURN"
    SCRAP = "SCRAP"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"


# Convenience set for validation
VALID_TRANSACTION_TYPES = {t.value for t in InventoryTransactionType}


# ---------------------------------------------------------------------------
# Response DTOs
# ---------------------------------------------------------------------------


@dataclass
class TransactionRecord:
    """Single inventory transaction entry."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    transaction_type: str
    quantity: Decimal
    reference_type: Optional[str]
    reference_id: Optional[uuid.UUID]
    warehouse_id: Optional[uuid.UUID]  # from_location_id or to_location_id
    batch_id: Optional[uuid.UUID]
    user_id: uuid.UUID
    timestamp: datetime
    notes: Optional[str]


@dataclass
class PaginatedTransactionResponse:
    """Paginated response for transaction queries."""

    items: List[TransactionRecord]
    total: int
    offset: int
    limit: int


@dataclass
class TransactionWithBalance:
    """A transaction record with its cumulative running balance."""

    transaction: TransactionRecord
    running_balance: Decimal


@dataclass
class ReconciliationStatus:
    """Result of comparing sum of transactions vs current_stock."""

    material_id: uuid.UUID
    transaction_sum: Decimal
    current_stock: Decimal
    difference: Decimal
    is_reconciled: bool
    tolerance: Decimal = field(default_factory=lambda: Decimal("0.001"))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class InventoryTransactionService:
    """Query service for inventory transaction history, running balance, and reconciliation.

    This service provides read-only query capabilities over the inventory_transactions table.
    Stock mutations continue to go through InventoryService (the canonical mutation gateway).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_transactions(
        self,
        tenant_id: uuid.UUID,
        material_id: Optional[uuid.UUID] = None,
        transaction_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> PaginatedTransactionResponse:
        """Retrieve paginated inventory transactions with optional filters.

        Args:
            tenant_id: Tenant scope for multi-tenancy isolation.
            material_id: Filter by specific material.
            transaction_type: Filter by transaction type (e.g. "FG_RECEIPT").
            date_from: Filter transactions on or after this timestamp.
            date_to: Filter transactions on or before this timestamp.
            reference_type: Filter by reference type (e.g. "work_order").
            reference_id: Filter by specific reference entity ID.
            offset: Pagination offset (default 0).
            limit: Page size (default 50, max 200).

        Returns:
            PaginatedTransactionResponse with items, total count, offset, and limit.
        """
        # Clamp limit
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        conditions = self._build_filter_conditions(
            tenant_id=tenant_id,
            material_id=material_id,
            transaction_type=transaction_type,
            date_from=date_from,
            date_to=date_to,
            reference_type=reference_type,
            reference_id=reference_id,
        )

        # Count total matching
        count_stmt = select(func.count(InventoryTransactionModel.id)).where(
            and_(*conditions)
        )
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch page
        query_stmt = (
            select(InventoryTransactionModel)
            .where(and_(*conditions))
            .order_by(InventoryTransactionModel.created_at.desc(), InventoryTransactionModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(query_stmt)
        rows = result.scalars().all()

        items = [self._to_record(row) for row in rows]

        return PaginatedTransactionResponse(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
        )

    async def get_running_balance(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> List[TransactionWithBalance]:
        """Compute cumulative running balance for a material ordered by timestamp.

        The running balance at position k = sum of all transaction quantities from
        T₁ to Tₖ (ordered by timestamp ascending, then ID ascending for tie-breaking).

        Args:
            tenant_id: Tenant scope.
            material_id: The material to compute running balance for.

        Returns:
            List of TransactionWithBalance ordered by timestamp ascending.
        """
        conditions = [
            InventoryTransactionModel.tenant_id == tenant_id,
            InventoryTransactionModel.material_id == material_id,
            InventoryTransactionModel.is_deleted.is_(False),
        ]

        stmt = (
            select(InventoryTransactionModel)
            .where(and_(*conditions))
            .order_by(
                InventoryTransactionModel.created_at.asc(),
                InventoryTransactionModel.id.asc(),
            )
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        running_balance = Decimal("0")
        items: List[TransactionWithBalance] = []

        for row in rows:
            qty = Decimal(str(row.quantity))
            running_balance += qty
            items.append(
                TransactionWithBalance(
                    transaction=self._to_record(row),
                    running_balance=running_balance,
                )
            )

        return items

    async def check_reconciliation(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> ReconciliationStatus:
        """Compare sum of all transactions for a material against its current_stock.

        If the absolute difference exceeds tolerance (0.001), the material is flagged
        as requiring reconciliation.

        Args:
            tenant_id: Tenant scope.
            material_id: The material to reconcile.

        Returns:
            ReconciliationStatus with comparison details.
        """
        tolerance = Decimal("0.001")

        # Sum all transaction quantities for this material
        sum_stmt = select(
            func.coalesce(
                func.sum(InventoryTransactionModel.quantity), 0
            )
        ).where(
            and_(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.material_id == material_id,
                InventoryTransactionModel.is_deleted.is_(False),
            )
        )
        sum_result = await self._session.execute(sum_stmt)
        transaction_sum = Decimal(str(sum_result.scalar_one()))

        # Get current_stock from material
        material_stmt = select(MaterialModel.current_stock).where(
            and_(
                MaterialModel.id == material_id,
                MaterialModel.tenant_id == tenant_id,
            )
        )
        material_result = await self._session.execute(material_stmt)
        current_stock_raw = material_result.scalar_one_or_none()

        if current_stock_raw is None:
            raise ValueError(f"Material {material_id} not found for tenant {tenant_id}")

        current_stock = Decimal(str(current_stock_raw))
        difference = abs(transaction_sum - current_stock)
        is_reconciled = difference <= tolerance

        return ReconciliationStatus(
            material_id=material_id,
            transaction_sum=transaction_sum,
            current_stock=current_stock,
            difference=difference,
            is_reconciled=is_reconciled,
            tolerance=tolerance,
        )

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _build_filter_conditions(
        self,
        tenant_id: uuid.UUID,
        material_id: Optional[uuid.UUID] = None,
        transaction_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
    ) -> list:
        """Build SQLAlchemy filter conditions from the given parameters."""
        conditions = [
            InventoryTransactionModel.tenant_id == tenant_id,
            InventoryTransactionModel.is_deleted.is_(False),
        ]

        if material_id is not None:
            conditions.append(InventoryTransactionModel.material_id == material_id)

        if transaction_type is not None:
            conditions.append(InventoryTransactionModel.transaction_type == transaction_type)

        if date_from is not None:
            conditions.append(InventoryTransactionModel.created_at >= date_from)

        if date_to is not None:
            conditions.append(InventoryTransactionModel.created_at <= date_to)

        if reference_type is not None:
            conditions.append(InventoryTransactionModel.reference_type == reference_type)

        if reference_id is not None:
            conditions.append(InventoryTransactionModel.reference_id == reference_id)

        return conditions

    @staticmethod
    def _to_record(model: InventoryTransactionModel) -> TransactionRecord:
        """Convert a persistence model to a TransactionRecord DTO."""
        # Determine warehouse_id from location fields
        warehouse_id = model.to_location_id or model.from_location_id

        return TransactionRecord(
            id=model.id,
            tenant_id=model.tenant_id,
            material_id=model.material_id,
            transaction_type=model.transaction_type,
            quantity=Decimal(str(model.quantity)),
            reference_type=model.reference_type,
            reference_id=model.reference_id,
            warehouse_id=warehouse_id,
            batch_id=model.batch_id,
            user_id=model.created_by,
            timestamp=model.created_at,
            notes=model.remarks,
        )
