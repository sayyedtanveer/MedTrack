from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


_GENERIC_RAW_MATERIAL_NAMES = {
    "raw material",
    "raw materials",
    "material",
    "materials",
    "component",
    "components",
    "item",
    "items",
}

_GENERIC_FINISHED_GOOD_NAMES = {
    "finished good",
    "finished goods",
    "product",
    "products",
    "final product",
    "finished item",
    "goods",
    "item",
    "items",
}


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_key(value: str) -> str:
    return _normalize_text(value).lower()


class MaterialType(str, Enum):
    RAW = "raw"
    FINISHED = "finished"
    SEMI_FINISHED = "semi_finished"


class Material(BaseEntity):
    """
    Core inventory item structured for the configurable schema.

    Domain rules enforced:
    - current_stock cannot go negative
    - reserved_stock cannot exceed current_stock
    - Every stock mutation is the caller's responsibility to log as a transaction
    """

    @staticmethod
    def normalize_code(value: str) -> str:
        normalized = _normalize_text(value)
        if not normalized:
            raise ValueError("Material code is required.")
        return normalized

    @staticmethod
    def normalize_name(value: str) -> str:
        normalized = _normalize_text(value)
        if not normalized:
            raise ValueError("Material name is required.")
        return normalized

    @staticmethod
    def coerce_material_type(value: MaterialType | str | None) -> MaterialType:
        if isinstance(value, MaterialType):
            return value

        normalized = _normalize_key(str(value or "")).replace(" ", "_")
        if normalized in {"raw", "raw_material", "raw-material", "rm"}:
            return MaterialType.RAW
        if normalized in {"finished", "finished_good", "finished_goods", "fg"}:
            return MaterialType.FINISHED
        if normalized in {"semi_finished", "semi-finished", "semifinished", "sf"}:
            return MaterialType.SEMI_FINISHED
        return MaterialType.RAW

    @classmethod
    def validate_name_for_type(cls, name: str, material_type: MaterialType | str | None) -> None:
        normalized_name = cls.normalize_name(name)
        normalized_type = cls.coerce_material_type(material_type)
        comparable_name = _normalize_key(normalized_name)

        blocked_names = (
            _GENERIC_RAW_MATERIAL_NAMES
            if normalized_type == MaterialType.RAW
            else _GENERIC_FINISHED_GOOD_NAMES
        )

        if comparable_name in blocked_names:
            if normalized_type == MaterialType.RAW:
                raise ValueError(
                    "Please use a specific raw material name like 'Brass Body', "
                    "'Glass Tube', or 'O-Ring Seal' instead of a generic label."
                )
            raise ValueError(
                "Please use a specific finished good name like 'Gear Rotameter - Standard' "
                "instead of a generic label."
            )

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        code: str,
        name: str,
        material_type: MaterialType = MaterialType.RAW,
        description: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        base_unit_id: Optional[uuid.UUID] = None,
        current_stock: Decimal = Decimal("0"),
        reserved_stock: Decimal = Decimal("0"),
        reorder_level: Optional[Decimal] = None,
        location_id: Optional[uuid.UUID] = None,
        is_batch_tracked: bool = False,
        is_serialized: bool = False,
        code_locked: bool = True,
        inspection_required: bool = False,
        inspection_template_id: Optional[uuid.UUID] = None,
        is_active: bool = True,
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
        self._code = self.normalize_code(code)
        self._name = self.normalize_name(name)
        self._material_type = self.coerce_material_type(material_type)
        self._description = description
        self._category_id = category_id
        self._base_unit_id = base_unit_id
        self._current_stock = Decimal(str(current_stock))
        self._reserved_stock = Decimal(str(reserved_stock))
        self._reorder_level = Decimal(str(reorder_level)) if reorder_level is not None else None
        self._location_id = location_id
        self._is_batch_tracked = is_batch_tracked
        self._is_serialized = is_serialized
        self._code_locked = code_locked
        self._inspection_required = inspection_required
        self._inspection_template_id = inspection_template_id
        self._is_active = is_active

    # ── Properties ──────────────────────────────────────────────────────────
    @property
    def code(self) -> str:
        return self._code

    @property
    def item_code(self) -> str:
        return self._code

    @property
    def item_type(self) -> str:
        if self._material_type == MaterialType.FINISHED:
            return "FG"
        if self._material_type == MaterialType.SEMI_FINISHED:
            return "SF"
        return "RAW"

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = self.normalize_name(value)
        self._touch()

    @property
    def material_type(self) -> MaterialType:
        return self._material_type

    @property
    def description(self) -> Optional[str]:
        return self._description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        self._description = value
        self._touch()

    @property
    def category_id(self) -> Optional[uuid.UUID]:
        return self._category_id

    @category_id.setter
    def category_id(self, value: Optional[uuid.UUID]) -> None:
        self._category_id = value
        self._touch()

    @property
    def base_unit_id(self) -> Optional[uuid.UUID]:
        return self._base_unit_id

    @base_unit_id.setter
    def base_unit_id(self, value: Optional[uuid.UUID]) -> None:
        self._base_unit_id = value
        self._touch()

    @property
    def current_stock(self) -> Decimal:
        return self._current_stock

    @property
    def reserved_stock(self) -> Decimal:
        return self._reserved_stock

    @property
    def reorder_level(self) -> Optional[Decimal]:
        return self._reorder_level

    @reorder_level.setter
    def reorder_level(self, value: Optional[Decimal]) -> None:
        self._reorder_level = value
        self._touch()

    @property
    def location_id(self) -> Optional[uuid.UUID]:
        return self._location_id

    @location_id.setter
    def location_id(self, value: Optional[uuid.UUID]) -> None:
        self._location_id = value
        self._touch()

    @property
    def is_batch_tracked(self) -> bool:
        return self._is_batch_tracked

    @is_batch_tracked.setter
    def is_batch_tracked(self, value: bool) -> None:
        self._is_batch_tracked = value
        self._touch()

    @property
    def is_serialized(self) -> bool:
        return self._is_serialized

    @is_serialized.setter
    def is_serialized(self, value: bool) -> None:
        self._is_serialized = value
        self._touch()

    @property
    def code_locked(self) -> bool:
        return self._code_locked

    @property
    def inspection_required(self) -> bool:
        return self._inspection_required

    @inspection_required.setter
    def inspection_required(self, value: bool) -> None:
        self._inspection_required = value
        self._touch()

    @property
    def inspection_template_id(self) -> Optional[uuid.UUID]:
        return self._inspection_template_id

    @inspection_template_id.setter
    def inspection_template_id(self, value: Optional[uuid.UUID]) -> None:
        self._inspection_template_id = value
        self._touch()

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = value
        self._touch()

    # ── Stock Mutation Methods ──────────────────────────────────────────────
    def increase_stock(self, quantity: Decimal) -> None:
        """Add stock (IN transaction). quantity must be positive."""
        if quantity <= Decimal("0"):
            raise ValueError("Quantity must be positive to increase stock.")
        self._current_stock += quantity
        self._touch()

    def decrease_stock(self, quantity: Decimal) -> None:
        """Remove stock (OUT transaction). Enforces no negative stock."""
        if quantity <= Decimal("0"):
            raise ValueError("Quantity must be positive to decrease stock.")
        available = self.get_available_stock()
        if quantity > available:
            raise ValueError(
                f"Insufficient available stock. Available: {available}, Requested: {quantity}"
            )
        self._current_stock -= quantity
        self._touch()

    def reserve_stock(self, quantity: Decimal) -> None:
        """Reserve stock for a future operation (e.g. a sales order)."""
        if quantity <= Decimal("0"):
            raise ValueError("Quantity must be positive to reserve stock.")
        if quantity > self.get_available_stock():
            raise ValueError(
                f"Cannot reserve {quantity}: only {self.get_available_stock()} available."
            )
        self._reserved_stock += quantity
        self._touch()

    def release_stock(self, quantity: Decimal) -> None:
        """Release a previously reserved quantity back to available pool."""
        if quantity <= Decimal("0"):
            raise ValueError("Quantity must be positive to release reserved stock.")
        if quantity > self._reserved_stock:
            raise ValueError(
                f"Cannot release {quantity}: only {self._reserved_stock} is reserved."
            )
        self._reserved_stock -= quantity
        self._touch()

    def get_available_stock(self) -> Decimal:
        """Available = current - reserved."""
        return self._current_stock - self._reserved_stock

    def adjust_stock(self, new_quantity: Decimal) -> Decimal:
        """
        Absolute stock adjustment. Returns the signed delta for transaction logging.
        This bypasses the reserve check — adjustment overrides everything.
        """
        if new_quantity < Decimal("0"):
            raise ValueError("Stock cannot be set below zero via adjustment.")
        delta = new_quantity - self._current_stock
        self._current_stock = new_quantity
        # If reserved now exceeds current due to adjustment, clamp it
        if self._reserved_stock > self._current_stock:
            self._reserved_stock = self._current_stock
        self._touch()
        return delta

    def is_low_stock(self) -> bool:
        """Returns True if current_stock is at or below reorder_level."""
        reorder = self._reorder_level
        if reorder is None:
            return False
        return self._current_stock <= reorder

    def update(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        base_unit_id: Optional[uuid.UUID] = None,
        material_type: Optional[MaterialType] = None,
        reorder_level: Optional[Decimal] = None,
        location_id: Optional[uuid.UUID] = None,
        is_batch_tracked: Optional[bool] = None,
        is_serialized: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> None:
        """Bulk update of editable fields."""
        if name is not None:
            self._name = self.normalize_name(name)
        if description is not None:
            self._description = description
        if category_id is not None:
            self._category_id = category_id
        if base_unit_id is not None:
            self._base_unit_id = base_unit_id
        if material_type is not None:
            self._material_type = self.coerce_material_type(material_type)
        if reorder_level is not None:
            self._reorder_level = reorder_level
        if location_id is not None:
            self._location_id = location_id
        if is_batch_tracked is not None:
            self._is_batch_tracked = is_batch_tracked
        if is_serialized is not None:
            self._is_serialized = is_serialized
        if is_active is not None:
            self._is_active = is_active
        self._touch()
