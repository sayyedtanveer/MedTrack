from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid


@dataclass(frozen=True)
class BulkCreateVariantsCommand:
    """Command to bulk create variants from import data."""
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    created_by: uuid.UUID
    variants_data: List[Dict[str, Any]]  # Each dict has: attribute_values, standard_cost, selling_price


@dataclass(frozen=True)
class BulkUpdateVariantsCommand:
    """Command to bulk update variants (pricing, status)."""
    tenant_id: uuid.UUID
    variants_data: List[Dict[str, Any]]  # Each dict has: id, standard_cost, selling_price, is_active


@dataclass(frozen=True)
class BulkActivateVariantsCommand:
    """Activate multiple variants."""
    tenant_id: uuid.UUID
    variant_ids: List[uuid.UUID]


@dataclass(frozen=True)
class BulkDeactivateVariantsCommand:
    """Deactivate multiple variants."""
    tenant_id: uuid.UUID
    variant_ids: List[uuid.UUID]
