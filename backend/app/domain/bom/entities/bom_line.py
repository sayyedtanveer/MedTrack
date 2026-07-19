from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class BOMLine(BaseEntity):
    def __init__(
        self,
        *,
        bom_id: uuid.UUID,
        quantity: Decimal,
        scrap_percentage: Decimal,
        tenant_id: Optional[uuid.UUID] = None,
        unit_id: Optional[uuid.UUID] = None,
        material_id: Optional[uuid.UUID] = None,
        template_id: Optional[uuid.UUID] = None,
        variant_id: Optional[uuid.UUID] = None,
        id: Optional[uuid.UUID] = None,
    ):
        super().__init__(id=id, tenant_id=tenant_id)
        self.bom_id = bom_id

        # Enforce that exactly one component reference is provided
        refs = [x for x in (material_id, template_id, variant_id) if x is not None]
        if len(refs) != 1:
            raise ValueError("BOMLine must reference exactly one of material_id, template_id, or variant_id.")

        self.material_id = material_id
        self.template_id = template_id
        self.variant_id = variant_id

        if quantity <= Decimal("0"):
            raise ValueError("BOMLine quantity must be greater than zero.")
        self.quantity = quantity

        if scrap_percentage < Decimal("0") or scrap_percentage > Decimal("100"):
            raise ValueError("BOMLine scrap_percentage must be between 0 and 100.")
        self.scrap_percentage = scrap_percentage

        self.unit_id = unit_id

    @property
    def component_id(self) -> uuid.UUID:
        """Gets the active component ID regardless of type."""
        return self.material_id or self.template_id or self.variant_id  # type: ignore
