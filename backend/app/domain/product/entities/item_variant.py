from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.domain.shared.base_entity import BaseEntity


def _build_variant_key(attr_keys_ordered: List[str], attribute_values: Dict[str, Any]) -> str:
    """
    Build a normalized, deterministic key from attribute_values.
    Follows template-defined attribute order.

    Example:
        attr_keys_ordered = ["SIZE", "COLOR"]
        attribute_values  = {"SIZE": "SMALL", "COLOR": "RED"}
        → "SIZE=SMALL|COLOR=RED"
    """
    parts: List[str] = []
    for key in attr_keys_ordered:
        val = attribute_values.get(key)
        if val is None:
            raise ValueError(f"Missing required attribute '{key}' in variant attribute_values.")
        parts.append(f"{key}={str(val).upper().strip()}")
    return "|".join(parts)


def _build_variant_code(template_code: str, attr_keys_ordered: List[str], attribute_values: Dict[str, Any]) -> str:
    """
    Auto-generate variant code from template code + attribute values.
    Example: "TSHIRT" + ["SIZE", "COLOR"] + {"SIZE": "SMALL", "COLOR": "RED"} → "TSHIRT-SMALL-RED"
    """
    suffix_parts = [str(attribute_values[k]).upper().strip() for k in attr_keys_ordered]
    return f"{template_code.upper()}-{'-'.join(suffix_parts)}"


def _build_variant_name(template_name: str, attr_keys_ordered: List[str], attribute_values: Dict[str, Any]) -> str:
    """
    Auto-generate display name.
    Example: "T-Shirt" + ["SIZE", "COLOR"] + {"SIZE": "Small", "COLOR": "Red"} → "T-Shirt - Small / Red"
    """
    val_parts = [str(attribute_values[k]).strip() for k in attr_keys_ordered]
    return f"{template_name} - {' / '.join(val_parts)}"


class ItemVariant(BaseEntity):
    """
    Represents a specific variant of an ItemTemplate.

    Domain Rules:
    - attribute_values must satisfy the template's attribute definitions
    - variant_key (normalized) must be unique per template per tenant (enforced at DB level)
    - code and name are auto-generated
    - standard_cost defaults to 0
    - selling_price is optional (can be None)
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        template_code: str,
        template_name: str,
        attribute_keys_ordered: List[str],
        attribute_values: Dict[str, Any],
        base_unit_id: Optional[uuid.UUID] = None,
        material_id: Optional[uuid.UUID] = None,
        standard_cost: Decimal = Decimal("0"),
        selling_price: Optional[Decimal] = None,
        # Can be supplied when rehydrating from DB (already computed)
        code: Optional[str] = None,
        name: Optional[str] = None,
        variant_key: Optional[str] = None,
        is_active: bool = True,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )

        # Normalise attribute keys to UPPER for consistent lookups
        normalised_values = {k.upper(): v for k, v in attribute_values.items()}
        ordered_keys = [k.upper() for k in attribute_keys_ordered]

        self._template_id = template_id
        self._attribute_values = normalised_values
        self._base_unit_id = base_unit_id
        self._material_id = material_id
        self._standard_cost = Decimal(str(standard_cost))
        self._selling_price = Decimal(str(selling_price)) if selling_price is not None else None
        self._is_active = is_active

        # Auto-generate or use supplied (for DB rehydration)
        self._variant_key  = variant_key  or _build_variant_key(ordered_keys, normalised_values)
        self._code         = code         or _build_variant_code(template_code, ordered_keys, normalised_values)
        self._name         = name         or _build_variant_name(template_name, ordered_keys, normalised_values)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def template_id(self) -> uuid.UUID:
        return self._template_id

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def variant_key(self) -> str:
        return self._variant_key

    @property
    def attribute_values(self) -> Dict[str, Any]:
        return dict(self._attribute_values)

    @property
    def base_unit_id(self) -> Optional[uuid.UUID]:
        return self._base_unit_id

    @property
    def material_id(self) -> Optional[uuid.UUID]:
        return self._material_id

    @property
    def standard_cost(self) -> Decimal:
        return self._standard_cost

    @property
    def selling_price(self) -> Optional[Decimal]:
        return self._selling_price

    @property
    def is_active(self) -> bool:
        return self._is_active

    # ── Behaviour ─────────────────────────────────────────────────────────────

    def update_pricing(
        self,
        *,
        standard_cost: Optional[Decimal] = None,
        selling_price: Optional[Decimal] = None,
    ) -> None:
        if standard_cost is not None:
            if standard_cost < Decimal("0"):
                raise ValueError("standard_cost cannot be negative.")
            self._standard_cost = standard_cost
        if selling_price is not None:
            if selling_price < Decimal("0"):
                raise ValueError("selling_price cannot be negative.")
            self._selling_price = selling_price
        self._touch()

    def activate(self) -> None:
        self._is_active = True
        self._touch()

    def deactivate(self) -> None:
        self._is_active = False
        self._touch()

    def set_material_link(self, material_id: Optional[uuid.UUID]) -> None:
        self._material_id = material_id
        self._touch()
