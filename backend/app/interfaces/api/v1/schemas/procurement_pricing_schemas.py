"""
Pydantic schemas for procurement pricing API (Phase 2).

Request validation and response serialization.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Supplier Price Agreement Schemas ──


class QuantityTierInput(BaseModel):
    """Quantity tier for tiered pricing."""
    min_qty: Decimal = Field(..., ge=0)
    max_qty: Optional[Decimal] = Field(None, ge=0)
    discount_percent: Decimal = Field(..., ge=0, le=100)


class CreateSupplierPriceAgreementRequest(BaseModel):
    """Create supplier price agreement."""
    supplier_id: uuid.UUID
    material_id: uuid.UUID
    base_price: Decimal = Field(..., gt=0)
    currency_code: str = Field(..., min_length=3, max_length=3)
    purchase_uom_id: Optional[uuid.UUID] = None
    minimum_order_quantity: Optional[Decimal] = Field(None, ge=0)
    effective_from: datetime
    effective_to: Optional[datetime] = None
    quantity_tiers: Optional[List[QuantityTierInput]] = None
    notes: Optional[str] = None


class SupplierPriceAgreementResponse(BaseModel):
    """Response for supplier price agreement."""
    id: uuid.UUID
    supplier_id: uuid.UUID
    material_id: uuid.UUID
    base_price: Decimal
    currency_code: str
    effective_from: datetime
    effective_to: Optional[datetime]
    quantity_tiers: Optional[List[dict]]
    purchase_uom_id: Optional[uuid.UUID] = None
    minimum_order_quantity: Optional[Decimal] = None
    notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class SubmitAgreementForApprovalRequest(BaseModel):
    """Submit agreement for approval."""
    pass  # No additional fields needed


class ApproveAgreementRequest(BaseModel):
    """Approve agreement."""
    pass  # No additional fields needed


class RejectAgreementRequest(BaseModel):
    """Reject agreement."""
    rejection_reason: str = Field(..., min_length=1, max_length=500)


class ActivateAgreementRequest(BaseModel):
    """Activate agreement."""
    pass  # No additional fields needed


class CancelAgreementRequest(BaseModel):
    """Cancel agreement."""
    cancellation_reason: str = Field(..., min_length=1, max_length=500)


# ── Standard Cost Revision Schemas ──


class InitializeStandardCostRequest(BaseModel):
    """Initialize material standard cost."""
    material_id: uuid.UUID
    initial_cost: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class CreateCostRevisionRequest(BaseModel):
    """Create standard cost revision."""
    material_id: uuid.UUID
    requested_cost: Decimal = Field(..., ge=0)
    reason: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = None


class ApproveCostRevisionRequest(BaseModel):
    """Approve cost revision."""
    pass  # No additional fields needed


class RejectCostRevisionRequest(BaseModel):
    """Reject cost revision."""
    rejection_reason: str = Field(..., min_length=1, max_length=500)


class CostRevisionResponse(BaseModel):
    """Response for cost revision."""
    id: uuid.UUID
    material_id: uuid.UUID
    requested_by: uuid.UUID
    requested_cost: Decimal
    current_cost: Decimal
    variance_percent: Optional[Decimal]
    reason: str
    notes: Optional[str]
    status: str
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime


class CreateCostRevisionResponse(CostRevisionResponse):
    """Response for a created revision; retains the original revision_id field."""
    revision_id: uuid.UUID


# ── Cost History Schemas ──


class MaterialCostHistoryResponse(BaseModel):
    """Response for cost history entry."""
    id: uuid.UUID
    material_id: uuid.UUID
    old_cost: Optional[Decimal]
    new_cost: Decimal
    variance_percent: Optional[Decimal]
    change_type: str
    source_type: str
    source_id: Optional[str]
    approved_by: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime


# ── Price Override Schemas ──


class PriceOverrideResponse(BaseModel):
    """Response for price override record."""
    id: uuid.UUID
    material_id: uuid.UUID
    grn_id: Optional[uuid.UUID]
    suggested_price: Decimal
    override_price: Decimal
    variance_percent: Decimal
    override_reason: str
    override_by: uuid.UUID
    notes: Optional[str]
    created_at: datetime


# ── Price Suggestion Schemas (6-Level Hierarchy) ──


class PriceSuggestionResponse(BaseModel):
    """Response for price suggestion from 6-level hierarchy."""
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    suggested_price: Decimal
    pricing_source: str  # SUPPLIER_AGREEMENT, QUOTATION, PURCHASE_HISTORY, BENCHMARK_ANY_SUPPLIER, STANDARD_COST, MANUAL
    confidence_level: str  # HIGH, MEDIUM, LOW
    level_number: int  # 1-6
    rationale: str  # Human-readable explanation
    currency_code: Optional[str] = None
    source_id: Optional[str] = None
    source_date: Optional[datetime] = None


class PricingAnalysisResponse(BaseModel):
    """Detailed analysis showing all 6 pricing levels."""
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    
    # Level 1: Supplier Agreement
    level_1_agreement_price: Optional[Decimal] = None
    level_1_agreement_status: Optional[str] = None
    
    # Level 2: Quotation
    level_2_quotation_price: Optional[Decimal] = None
    level_2_quotation_status: Optional[str] = None
    
    # Level 3: Purchase History (Same Supplier)
    level_3_grn_price: Optional[Decimal] = None
    level_3_grn_date: Optional[datetime] = None
    
    # Level 4: Benchmarking (Any Supplier)
    level_4_benchmark_price: Optional[Decimal] = None
    level_4_benchmark_supplier_id: Optional[uuid.UUID] = None
    
    # Level 5: Standard Cost
    level_5_standard_cost: Optional[Decimal] = None
    level_5_standard_cost_status: Optional[str] = None
    
    # Selected suggestion
    selected_price: Optional[Decimal] = None
    selected_source: Optional[str] = None
    selected_confidence: Optional[str] = None
    
    analysis_timestamp: datetime


class GetPricingSuggestionsRequest(BaseModel):
    """Request for pricing suggestions."""
    material_id: uuid.UUID
    supplier_id: uuid.UUID


class RecordMaterialPriceOverrideRequest(BaseModel):
    """Existing material/GRN override contract, separate from supplier analytics."""
    material_id: uuid.UUID
    grn_id: Optional[uuid.UUID] = None
    suggested_price: Decimal = Field(..., gt=0)
    override_price: Decimal = Field(..., gt=0)
    override_reason: str = Field(..., min_length=1)
    notes: Optional[str] = None


class RecordPriceOverrideRequest(BaseModel):
    """Record a price override."""
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    original_suggested_price: Decimal
    override_price: Decimal
    override_reason: Optional[str] = None
    override_source: Optional[str] = None
    notes: Optional[str] = None


class RecordedPriceOverrideResponse(BaseModel):
    """Response after recording price override."""
    id: uuid.UUID
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    original_suggested_price: Decimal
    override_price: Decimal
    variance_percent: Decimal
    override_reason: Optional[str]
    override_source: Optional[str]
    overridden_by: uuid.UUID
    created_at: datetime


class PriceOverrideHistoryResponse(BaseModel):
    """Price override history for material-supplier pair."""
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    overrides: List[RecordedPriceOverrideResponse]
    total_count: int
    average_override_price: Optional[Decimal] = None
    min_override_price: Optional[Decimal] = None
    max_override_price: Optional[Decimal] = None


class OverrideStatisticsResponse(BaseModel):
    """Statistics on price overrides."""
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    total_overrides: int
    average_override_price: Optional[Decimal] = None
    min_override_price: Optional[Decimal] = None
    max_override_price: Optional[Decimal] = None
    median_override_price: Optional[Decimal] = None
    std_dev: Optional[Decimal] = None


class OverrideTrendResponse(BaseModel):
    """Trend analysis for price overrides."""
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    trend_direction: str  # UPWARD, DOWNWARD, STABLE, INSUFFICIENT_DATA
    total_records_analyzed: int
    time_period_days: Optional[int] = None
    price_change_percent: Optional[Decimal] = None
    trend_confidence: str  # HIGH, MEDIUM, LOW
    analysis_timestamp: datetime


# ── List Response Schemas ──


class ListSupplierAgreementsResponse(BaseModel):
    """Response for listing supplier agreements."""
    items: List[SupplierPriceAgreementResponse]
    total: int
    page: int
    page_size: int


class ListCostRevisionsResponse(BaseModel):
    """Response for listing cost revisions."""
    items: List[CostRevisionResponse]
    total: int
    page: int
    page_size: int


class ListCostHistoryResponse(BaseModel):
    """Response for listing cost history."""
    items: List[MaterialCostHistoryResponse]
    total: int


class ListPriceOverridesResponse(BaseModel):
    """Response for listing price overrides."""
    items: List[PriceOverrideResponse]
    total: int


# ── Error Response Schema ──


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    code: Optional[str] = None
    status_code: int
