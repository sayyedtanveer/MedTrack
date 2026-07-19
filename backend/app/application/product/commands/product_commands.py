from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from backend.app.domain.product.value_objects.product_status import ProductStatus


# ── Item Template Commands ────────────────────────────────────────────────────

@dataclass(frozen=True)
class CreateItemTemplateCommand:
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    status: ProductStatus = ProductStatus.DRAFT


@dataclass(frozen=True)
class UpdateItemTemplateCommand:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    attributes: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    status: Optional[ProductStatus] = None


@dataclass(frozen=True)
class ChangeProductStatusCommand:
    """Command to explicitly change product status."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    new_status: ProductStatus


# ── Item Variant Commands ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class CreateItemVariantCommand:
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    created_by: uuid.UUID
    attribute_values: Dict[str, Any]
    base_unit_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    standard_cost: Decimal = Decimal("0")
    selling_price: Optional[Decimal] = None


@dataclass(frozen=True)
class UpdateItemVariantCommand:
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: Optional[uuid.UUID] = None
    standard_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    is_active: Optional[bool] = None
