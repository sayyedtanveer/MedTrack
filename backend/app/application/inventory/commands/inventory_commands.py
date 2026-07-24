from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

# Sentinel: "field not provided" vs explicit None (e.g. clear inspection_template_id)
MISSING = object()


@dataclass(frozen=True)
class CreateMaterialCommand:
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    code: Optional[str] = None
    material_type: str = "raw"
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    reorder_level: Optional[Decimal] = None
    location_id: Optional[uuid.UUID] = None
    is_batch_tracked: bool = False
    is_serialized: bool = False
    opening_stock: Optional[Decimal] = None


@dataclass(frozen=True)
class UpdateMaterialCommand:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    material_type: Optional[str] = None
    reorder_level: Optional[Decimal] = None
    location_id: Optional[uuid.UUID] = None
    is_batch_tracked: Optional[bool] = None
    is_serialized: Optional[bool] = None
    is_active: Optional[bool] = None
    current_cost: Optional[Decimal] = None
    inspection_required: Any = field(default=MISSING)
    inspection_template_id: Any = field(default=MISSING)
    # Code immutability: MISSING means "not provided" (retain existing), explicit value triggers check
    code: Any = field(default=MISSING)


@dataclass(frozen=True)
class AddStockCommand:
    """Stock IN — increases current_stock."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal
    created_by: uuid.UUID
    unit_id: Optional[uuid.UUID] = None
    to_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class RemoveStockCommand:
    """Stock OUT — decreases current_stock. Enforces no-negative rule."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal
    created_by: uuid.UUID
    unit_id: Optional[uuid.UUID] = None
    from_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class AdjustStockCommand:
    """Absolute stock override — sets current_stock to new_quantity."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    new_quantity: Decimal
    created_by: uuid.UUID
    unit_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None


# ── Phase 1.2 — Batch Commands ────────────────────────────────────────────

@dataclass(frozen=True)
class AddStockWithBatchCommand:
    """Stock IN for a batch-tracked material — creates/updates a Batch record."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    batch_number: str
    quantity: Decimal
    created_by: uuid.UUID
    expiry_date: Optional[date] = None
    unit_id: Optional[uuid.UUID] = None
    to_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class RemoveStockFromBatchCommand:
    """Stock OUT from a specific batch — enforces batch-level no-negative rule."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    batch_number: str
    quantity: Decimal
    created_by: uuid.UUID
    unit_id: Optional[uuid.UUID] = None
    from_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None


# ── Phase 1.3 — Serial Commands ────────────────────────────────────────────

@dataclass(frozen=True)
class AddSerialStockCommand:
    """Register one or more new serial numbers for a serialised material."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    serial_numbers: List[str]
    created_by: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None


@dataclass(frozen=True)
class IssueSerialCommand:
    """Issue a single serial number (IN_STOCK/RETURNED → ISSUED)."""
    tenant_id: uuid.UUID
    serial_number: str
    created_by: uuid.UUID
    reference_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None


@dataclass(frozen=True)
class ReturnSerialCommand:
    """Return a single issued serial number (ISSUED → RETURNED)."""
    tenant_id: uuid.UUID
    serial_number: str
    created_by: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
