from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class TransactionType(str, Enum):
    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    # Extended transaction types for full traceability (Requirement 31.1, 31.2)
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


class ReferenceType(str, Enum):
    MANUAL = "manual"
    ADJUSTMENT = "adjustment"
    PURCHASE_ORDER = "purchase_order"
    SALES_ORDER = "sales_order"
    WORK_ORDER = "work_order"
    OPENING_BALANCE = "opening_balance"


class InventoryTransaction(BaseEntity):
    """
    Immutable audit record for every stock change on a Material.

    One transaction is created per stock operation:
    - IN  → AddStock / receive goods
    - OUT → RemoveStock / issue materials
    - ADJUSTMENT → SetStock / cycle count override
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        material_id: uuid.UUID,
        transaction_type: TransactionType,
        quantity: Decimal,
        unit_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        from_location_id: Optional[uuid.UUID] = None,
        to_location_id: Optional[uuid.UUID] = None,
        reference_type: ReferenceType = ReferenceType.MANUAL,
        reference_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        created_by: uuid.UUID,
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
        self._material_id = material_id
        self._transaction_type = transaction_type
        self._quantity = Decimal(str(quantity))
        self._unit_id = unit_id
        self._batch_id = batch_id
        self._from_location_id = from_location_id
        self._to_location_id = to_location_id
        self._reference_type = reference_type
        self._reference_id = reference_id
        self._remarks = remarks
        self._created_by = created_by

    # ── Properties ──────────────────────────────────────────────────────────
    @property
    def material_id(self) -> uuid.UUID:
        return self._material_id

    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def unit_id(self) -> Optional[uuid.UUID]:
        return self._unit_id

    @property
    def batch_id(self) -> Optional[uuid.UUID]:
        return self._batch_id

    @property
    def from_location_id(self) -> Optional[uuid.UUID]:
        return self._from_location_id

    @property
    def to_location_id(self) -> Optional[uuid.UUID]:
        return self._to_location_id

    @property
    def reference_type(self) -> ReferenceType:
        return self._reference_type

    @property
    def reference_id(self) -> Optional[uuid.UUID]:
        return self._reference_id

    @property
    def remarks(self) -> Optional[str]:
        return self._remarks

    @property
    def created_by(self) -> uuid.UUID:
        return self._created_by
