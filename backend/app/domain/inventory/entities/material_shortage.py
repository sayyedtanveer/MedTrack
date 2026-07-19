"""Material Shortage entity for tracking material shortages in work orders."""
from __future__ import annotations

import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


class ShortageStatus(str, enum.Enum):
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"


class MaterialShortage:
    """Represents a material shortage for a work order."""

    def __init__(
        self,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        work_order_id: uuid.UUID,
        material_id: uuid.UUID,
        required_quantity: Decimal,
        available_quantity: Decimal,
        shortage_quantity: Decimal,
        status: ShortageStatus,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.tenant_id = tenant_id
        self.work_order_id = work_order_id
        self.material_id = material_id
        self.required_quantity = required_quantity
        self.available_quantity = available_quantity
        self.shortage_quantity = shortage_quantity
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def calculate_shortage(self, required: Decimal, available: Decimal) -> Decimal:
        """Calculate shortage quantity."""
        shortage = required - available
        return max(Decimal("0"), shortage)

    def close_shortage(self) -> None:
        """Close the shortage record."""
        if self.status == ShortageStatus.CLOSED:
            raise ValueError("Shortage is already closed")
        self.status = ShortageStatus.CLOSED
        self.updated_at = datetime.now(timezone.utc)

    def partial_fulfill(self, fulfilled_quantity: Decimal) -> None:
        """Partially fulfill the shortage."""
        if self.status == ShortageStatus.CLOSED:
            raise ValueError("Cannot fulfill closed shortage")

        self.shortage_quantity = max(Decimal("0"), self.shortage_quantity - fulfilled_quantity)
        self.available_quantity += fulfilled_quantity

        if self.shortage_quantity == Decimal("0"):
            self.status = ShortageStatus.CLOSED
        else:
            self.status = ShortageStatus.PARTIAL

        self.updated_at = datetime.now(timezone.utc)
