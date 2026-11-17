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


async def get_variant_template_id(
    session,
    tenant_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> Optional[uuid.UUID]:
    """Return the template_id for a variant, used for Option-B parent-price fallback.

    Returns the template_id UUID if the variant exists and is active, or None
    if the variant is not found, deleted, or the template_id is unset.

    Used by PricingService to perform a within-list parent fallback lookup:
    when a price list contains the parent template price but not the variant price,
    this provider resolves which template to look up.

    Requirements: Phase 1 — Option B pricing policy
    """
    stmt = select(ItemVariantModel.template_id).where(
        ItemVariantModel.id == variant_id,
        ItemVariantModel.tenant_id == tenant_id,
        ItemVariantModel.is_deleted.is_(False),
        ItemVariantModel.is_active.is_(True),
    )
    result = await session.execute(stmt)
    template_id = result.scalar_one_or_none()
    return template_id if template_id is not None else None
