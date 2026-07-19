from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class BatchStatus(str, Enum):
    IN_STOCK = "in_stock"
    DEPLETED = "depleted"
    EXPIRED = "expired"
    # Enterprise lifecycle (maps to DB status values)
    AVAILABLE = "available"
    RESERVED = "reserved"
    PARTIALLY_CONSUMED = "partially_consumed"
    FULLY_CONSUMED = "fully_consumed"
    RETURNED = "returned"
    QUARANTINED = "quarantined"


class Batch(BaseEntity):
    """
    Represents a batch of stock for a batch-tracked material.

    Domain rules enforced:
    - batch_number is required and immutable after creation
    - expiry_date must be a future date on creation
    - quantity cannot go negative
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        material_id: uuid.UUID,
        batch_number: str,
        quantity: Decimal = Decimal("0"),
        remaining_quantity: Optional[Decimal] = None,
        expiry_date: Optional[date] = None,
        location_id: Optional[uuid.UUID] = None,
        status: BatchStatus = BatchStatus.IN_STOCK,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        if not batch_number or not batch_number.strip():
            raise ValueError("batch_number is required.")
        if expiry_date is not None and expiry_date <= date.today():
            raise ValueError("expiry_date must be a future date.")

        self._material_id = material_id
        self._batch_number = batch_number.strip()
        self._quantity = Decimal(str(quantity))
        self._remaining_quantity = (
            Decimal(str(remaining_quantity)) if remaining_quantity is not None else Decimal(str(quantity))
        )
        self._expiry_date = expiry_date
        self._location_id = location_id
        self._status: BatchStatus = BatchStatus(status) if isinstance(status, str) else status

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def material_id(self) -> uuid.UUID:
        return self._material_id

    @property
    def batch_number(self) -> str:
        return self._batch_number

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def remaining_quantity(self) -> Decimal:
        return self._remaining_quantity

    @property
    def expiry_date(self) -> Optional[date]:
        return self._expiry_date

    @property
    def location_id(self) -> Optional[uuid.UUID]:
        return self._location_id

    @property
    def status(self) -> BatchStatus:
        return self._status

    # ── Quantity Mutations ───────────────────────────────────────────────────

    def increase_quantity(self, qty: Decimal) -> None:
        """Add stock to this batch. qty must be positive."""
        if qty <= Decimal("0"):
            raise ValueError("qty must be positive to increase batch quantity.")
        self._quantity += qty
        self._remaining_quantity += qty
        self._touch()

    def decrease_quantity(self, qty: Decimal) -> None:
        """Remove stock from this batch. Enforces no-negative rule."""
        if qty <= Decimal("0"):
            raise ValueError("qty must be positive to decrease batch quantity.")
        if qty > self._remaining_quantity:
            raise ValueError(
                f"Insufficient batch stock. Available: {self._remaining_quantity}, Requested: {qty}"
            )
        self._remaining_quantity -= qty
        if self._remaining_quantity == Decimal("0"):
            self._status = BatchStatus.DEPLETED
        self._touch()

    # ── Convenience ─────────────────────────────────────────────────────────

    def is_expired(self) -> bool:
        """Returns True if the batch has expired."""
        expiry = self._expiry_date
        if expiry is None:
            return False
        return expiry < date.today()

    def days_until_expiry(self) -> Optional[int]:
        """Returns number of days until expiry, or None if not set. Negative if already expired."""
        expiry = self._expiry_date
        if expiry is None:
            return None
        return (expiry - date.today()).days
