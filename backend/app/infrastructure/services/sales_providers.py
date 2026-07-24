"""
Sales infrastructure providers.

Provides data-access helpers for the Sales domain that sit outside the
repository layer — typically lightweight scalar queries wired into domain
services (e.g. PricingService) via partial application or protocol injection.
"""

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel


async def get_variant_selling_price(
    session,
    tenant_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> Optional[Decimal]:
    """Fetch item_variant.selling_price for tier-3 price resolution.

    Returns the selling_price as a Decimal if it exists and the variant is
    active, or None if the variant is not found, inactive, deleted, or has
    no selling_price set.

    Requirements: REQ-SP-004 AC1
    """
    stmt = select(ItemVariantModel.selling_price).where(
        ItemVariantModel.id == variant_id,
        ItemVariantModel.tenant_id == tenant_id,
        ItemVariantModel.is_deleted.is_(False),
        ItemVariantModel.is_active.is_(True),
    )
    result = await session.execute(stmt)
    price = result.scalar_one_or_none()
    return Decimal(str(price)) if price is not None else None
