"""
Procurement pricing queries (Phase 2 application layer).

All queries are frozen dataclasses (immutable).
Queries represent intentions to read state (CQRS read operations, no mutations).
"""

import uuid
from dataclasses import dataclass
from typing import Optional


# ── Supplier Price Agreement Queries ──


@dataclass(frozen=True)
class GetSupplierPriceAgreementQuery:
    """Get a specific supplier price agreement."""
    tenant_id: uuid.UUID
    agreement_id: uuid.UUID


@dataclass(frozen=True)
class ListSupplierPriceAgreementsQuery:
    """List all supplier price agreements with optional filters."""
    tenant_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    status: Optional[str] = None  # DRAFT, PENDING, APPROVED, ACTIVE, EXPIRED, CANCELLED
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class GetActivePriceAgreementQuery:
    """Get currently active price agreement for supplier-material pair."""
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    material_id: uuid.UUID


# ── Standard Cost Revision Queries ──


@dataclass(frozen=True)
class GetStandardCostRevisionQuery:
    """Get a specific cost revision."""
    tenant_id: uuid.UUID
    revision_id: uuid.UUID


@dataclass(frozen=True)
class ListPendingCostRevisionsQuery:
    """List pending cost revisions awaiting approval."""
    tenant_id: uuid.UUID
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class ListMaterialCostRevisionsQuery:
    """List all cost revisions for a material (all statuses)."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    page: int = 1
    page_size: int = 20


# ── Material Cost History Queries ──


@dataclass(frozen=True)
class GetMaterialCostHistoryQuery:
    """Get immutable cost change history for a material."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    limit: int = 100


@dataclass(frozen=True)
class GetCostHistoryByChangeTypeQuery:
    """Get cost history filtered by change type."""
    tenant_id: uuid.UUID
    change_type: str  # GRN_RECEIPT, COST_REVISION_APPROVED, etc.
    limit: int = 100


# ── Price Suggestion Queries ──


@dataclass(frozen=True)
class GetPriceSuggestionQuery:
    """Get suggested price for a material (applies price priority logic)."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None  # If provided, prioritize this supplier
    quantity: Optional[int] = None  # For tiered pricing application
    include_source_info: bool = True  # Include origin (agreement/quotation/GRN/etc.)


# ── Price Override History Queries ──


@dataclass(frozen=True)
class ListPriceOverridesQuery:
    """List price override records for analytics."""
    tenant_id: uuid.UUID
    material_id: Optional[uuid.UUID] = None
    grn_id: Optional[uuid.UUID] = None
    limit: int = 100
