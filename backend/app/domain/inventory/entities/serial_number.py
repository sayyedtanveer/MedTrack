from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class SerialStatus(str, Enum):
    IN_STOCK = "in_stock"
    ISSUED = "issued"
    RETURNED = "returned"


class SerialNumber(BaseEntity):
    """
    Tracks an individual serialised unit of a material.

    Domain rules enforced:
    - serial_number is required and unique per tenant
    - is_serialized must be True on the parent material before creating serials
    - Status transitions: IN_STOCK → ISSUED → RETURNED → IN_STOCK
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        material_id: uuid.UUID,
        serial_number: str,
        status: SerialStatus = SerialStatus.IN_STOCK,
        current_location_id: Optional[uuid.UUID] = None,
        reference_id: Optional[uuid.UUID] = None,
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
        if not serial_number or not serial_number.strip():
            raise ValueError("serial_number is required.")

        self._material_id = material_id
        self._serial_number = serial_number.strip()
        self._status: SerialStatus = SerialStatus(status) if isinstance(status, str) else status
        self._current_location_id = current_location_id
        self._reference_id = reference_id

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def material_id(self) -> uuid.UUID:
        return self._material_id

    @property
    def serial_number(self) -> str:
        return self._serial_number

    @property
    def status(self) -> SerialStatus:
        return self._status

    @property
    def current_location_id(self) -> Optional[uuid.UUID]:
        return self._current_location_id

    @property
    def reference_id(self) -> Optional[uuid.UUID]:
        return self._reference_id

    # ── State Transitions ────────────────────────────────────────────────────

    def issue(
        self,
        *,
        reference_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Mark serial as ISSUED. Must be IN_STOCK or RETURNED."""
        if self._status not in (SerialStatus.IN_STOCK, SerialStatus.RETURNED):
            raise ValueError(
                f"Cannot issue serial '{self._serial_number}': current status is '{self._status}'."
            )
        self._status = SerialStatus.ISSUED
        self._reference_id = reference_id
        self._current_location_id = location_id
        self._touch()

    def return_item(self, *, location_id: Optional[uuid.UUID] = None) -> None:
        """Mark serial as RETURNED. Must be ISSUED."""
        if self._status != SerialStatus.ISSUED:
            raise ValueError(
                f"Cannot return serial '{self._serial_number}': current status is '{self._status}'."
            )
        self._status = SerialStatus.RETURNED
        self._current_location_id = location_id
        self._reference_id = None
        self._touch()

    def put_back_in_stock(self, *, location_id: Optional[uuid.UUID] = None) -> None:
        """Move a RETURNED serial back to IN_STOCK."""
        if self._status != SerialStatus.RETURNED:
            raise ValueError(
                f"Cannot restock serial '{self._serial_number}': current status is '{self._status}'."
            )
        self._status = SerialStatus.IN_STOCK
        self._current_location_id = location_id
        self._touch()

    def is_available(self) -> bool:
        """Returns True if the serial can be issued (IN_STOCK or RETURNED)."""
        return self._status in (SerialStatus.IN_STOCK, SerialStatus.RETURNED)
