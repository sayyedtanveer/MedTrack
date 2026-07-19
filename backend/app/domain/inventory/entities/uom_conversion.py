from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class UomConversion(BaseEntity):
    """
    Conversion factor between two units of measure.
    Multiplier logic: 1 from_uom = conversion_factor * to_uom
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        from_uom_id: uuid.UUID,
        to_uom_id: uuid.UUID,
        conversion_factor: Decimal,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
        )
        if conversion_factor <= Decimal("0"):
            raise ValueError("Conversion factor must be greater than zero")
            
        self._from_uom_id = from_uom_id
        self._to_uom_id = to_uom_id
        self._conversion_factor = Decimal(str(conversion_factor))

    @property
    def from_uom_id(self) -> uuid.UUID:
        return self._from_uom_id

    @property
    def to_uom_id(self) -> uuid.UUID:
        return self._to_uom_id

    @property
    def conversion_factor(self) -> Decimal:
        return self._conversion_factor

    def update_factor(self, factor: Decimal) -> None:
        if factor <= Decimal("0"):
            raise ValueError("Conversion factor must be greater than zero")
        self._conversion_factor = factor
        self._touch()
