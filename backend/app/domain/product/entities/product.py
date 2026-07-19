from __future__ import annotations

import uuid
from typing import Optional

from backend.app.domain.product.entities.item_template import ItemTemplate
from backend.app.domain.product.entities.item_variant import ItemVariant


ProductTemplate = ItemTemplate


class ProductVariant(ItemVariant):
    """Backward-compatible facade for the old ProductVariant constructor."""

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        variant_key: str,
        sku: str,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            template_id=template_id,
            template_code=sku,
            template_name=sku,
            attribute_keys_ordered=[],
            attribute_values={},
            code=sku,
            name=sku,
            variant_key=variant_key,
        )
        self._sku = sku

    @property
    def sku(self) -> str:
        return self._sku
