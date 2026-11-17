"""
Purchase Order (PO) 6-level pricing engine for Priority 2.

This orchestrator service implements the 6-level pricing priority system:
1. Active supplier agreement (APPROVED/ACTIVE status)
2. Approved supplier quotation (APPROVED/AWARDED status)
3. Latest purchase from same supplier (GRN history)
4. Latest purchase from any supplier (GRN history, benchmarking)
5. Approved standard cost (APPROVED status)
6. Manual pricing (default fallback)

The engine is called during PO line creation to suggest/calculate unit_price
based on the available pricing data. It returns a PricingDecision with the
recommended price, rationale, and source of pricing.

Used by:
- PO creation/edit screen (GET /purchase-orders/pricing-suggestion)
- PO line save (auto-calculate if not manually overridden)
"""
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.quotation_lookup_service import (
    SupplierQuotationLookupService,
)
from backend.app.application.procurement.pricing.purchase_history_lookup_service import (
    PurchaseHistoryLookupService,
)
from backend.app.application.procurement.pricing.any_supplier_history_lookup_service import (
    AnySupplierHistoryLookupService,
)
from backend.app.infrastructure.persistence.repositories.procurement_pricing_repository import (
    SupplierPriceAgreementRepository,
    StandardCostRevisionRepository,
)


@dataclass
class PricingDecision:
    """Decision from the 6-level pricing engine."""
    
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    suggested_price: Optional[Decimal]  # Renamed from recommended_price
    level_number: int  # 1-6, where 1 is highest priority (best source) - renamed from priority_level
    pricing_source: str  # "SUPPLIER_AGREEMENT", "QUOTATION", "PURCHASE_HISTORY", "BENCHMARK_ANY_SUPPLIER", "STANDARD_COST", "MANUAL" - renamed from source
    confidence_level: str  # "HIGH", "MEDIUM", "LOW" - NEW FIELD
    rationale: str  # Human-readable explanation
    
    # Metadata for frontend display
    agreement_id: Optional[uuid.UUID] = None
    quotation_id: Optional[uuid.UUID] = None
    grn_number: Optional[str] = None
    po_number: Optional[str] = None
    
    # Benchmarking data
    best_price_available: Optional[Decimal] = None
    best_supplier: Optional[str] = None
    total_suppliers: int = 0
    
    # Approval status
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "material_id": str(self.material_id),
            "supplier_id": str(self.supplier_id),
            "suggested_price": float(self.suggested_price) if self.suggested_price else None,
            "level_number": self.level_number,
            "pricing_source": self.pricing_source,
            "confidence_level": self.confidence_level,
            "rationale": self.rationale,
            "agreement_id": str(self.agreement_id) if self.agreement_id else None,
            "quotation_id": str(self.quotation_id) if self.quotation_id else None,
            "grn_number": self.grn_number,
            "po_number": self.po_number,
            "best_price_available": float(self.best_price_available) if self.best_price_available else None,
            "best_supplier": self.best_supplier,
            "total_suppliers": self.total_suppliers,
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
        }


class POPricingEngine:
    """
    6-level pricing orchestrator for PO line items.
    
    Applies pricing priorities in order:
    1. Active supplier agreement
    2. Approved quotation
    3. Latest purchase (same supplier)
    4. Latest purchase (any supplier)
    5. Approved standard cost
    6. Manual (no suggestion)
    """
    
    def __init__(
        self,
        quotation_service: SupplierQuotationLookupService,
        history_service: PurchaseHistoryLookupService,
        any_supplier_service: AnySupplierHistoryLookupService,
    ):
        """Initialize with injected dependencies (DDD pattern)."""
        self.quotation_service = quotation_service
        self.same_supplier_service = history_service
        self.any_supplier_service = any_supplier_service
        # Services will provide session internally
    
    async def calculate_pricing(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        supplier_id: uuid.UUID,
        quantity: Optional[Decimal] = None,
    ) -> Optional['PricingDecision']:
        """
        Calculate recommended price for a PO line using 6-level priority.
        
        Args:
            tenant_id: Tenant context
            material_id: Material being ordered
            supplier_id: Supplier being ordered from
            quantity: Optional quantity for volume-based pricing (future enhancement)
        
        Returns:
            PricingDecision with recommended price and source, or None if no pricing available
        """
        # Priority 1: Active supplier agreement (HIGH confidence)
        # Note: We need to get session from quotation_service for queries
        # This is a limitation of current design - we rely on services having session
        agreement = None
        if hasattr(self.quotation_service, '_session'):
            agreement_repo = SupplierPriceAgreementRepository(self.quotation_service._session)
            agreement = await agreement_repo.get_active_by_supplier_material(
                tenant_id, supplier_id, material_id
            )
        
        if agreement and agreement.status == "ACTIVE":
            return PricingDecision(
                material_id=material_id,
                supplier_id=supplier_id,
                suggested_price=agreement.get_price_for_quantity(quantity or Decimal("0")),
                level_number=1,
                pricing_source="SUPPLIER_AGREEMENT",
                confidence_level="HIGH",
                rationale=f"Active supplier agreement #{agreement.id}",
                agreement_id=agreement.id,
            )
        
        # Priority 2: Approved quotation (MEDIUM confidence)
        quotation_result = await self.quotation_service.lookup_by_supplier_and_material(
            tenant_id, supplier_id, material_id
        )
        if quotation_result.found:
            # Get benchmarking data
            any_supplier_result = await self.any_supplier_service.lookup_latest_purchase_any_supplier(
                tenant_id, material_id
            )
            
            return PricingDecision(
                material_id=material_id,
                supplier_id=supplier_id,
                suggested_price=quotation_result.unit_price,
                level_number=2,
                pricing_source="QUOTATION",
                confidence_level="MEDIUM",
                rationale=f"Approved quotation {quotation_result.quotation_number}",
                quotation_id=quotation_result.quotation_id,
                best_price_available=any_supplier_result.best_price if any_supplier_result.found else None,
                best_supplier=any_supplier_result.best_supplier_name if any_supplier_result.found else None,
                total_suppliers=any_supplier_result.total_suppliers if any_supplier_result.found else 0,
            )
        
        # Priority 3: Latest purchase from same supplier (MEDIUM confidence)
        same_supplier_result = await self.same_supplier_service.lookup_by_supplier_and_material(
            tenant_id, supplier_id, material_id
        )
        if same_supplier_result.found:
            any_supplier_result = await self.any_supplier_service.lookup_latest_purchase_any_supplier(
                tenant_id, material_id
            )
            
            return PricingDecision(
                material_id=material_id,
                supplier_id=supplier_id,
                suggested_price=same_supplier_result.unit_price,
                level_number=3,
                pricing_source="PURCHASE_HISTORY",
                confidence_level="MEDIUM",
                rationale=f"Latest purchase from this supplier: {same_supplier_result.grn_number}",
                grn_number=same_supplier_result.grn_number,
                po_number=same_supplier_result.po_number,
                best_price_available=any_supplier_result.best_price if any_supplier_result.found else None,
                best_supplier=any_supplier_result.best_supplier_name if any_supplier_result.found else None,
                total_suppliers=any_supplier_result.total_suppliers if any_supplier_result.found else 0,
            )
        
        # Priority 4: Latest purchase from any supplier (LOW confidence)
        any_supplier_result = await self.any_supplier_service.lookup_latest_purchase_any_supplier(
            tenant_id, material_id
        )
        if any_supplier_result.found:
            return PricingDecision(
                material_id=material_id,
                supplier_id=supplier_id,
                suggested_price=any_supplier_result.unit_price,
                level_number=4,
                pricing_source="BENCHMARK_ANY_SUPPLIER",
                confidence_level="LOW",
                rationale=f"Latest purchase from any supplier: {any_supplier_result.grn_number}",
                grn_number=any_supplier_result.grn_number,
                po_number=any_supplier_result.po_number,
                best_price_available=any_supplier_result.best_price,
                best_supplier=any_supplier_result.best_supplier_name,
                total_suppliers=any_supplier_result.total_suppliers,
            )
        
        # Priority 5: Approved standard cost (LOW confidence)
        cost_revision = None
        if hasattr(self.quotation_service, '_session'):
            cost_repo = StandardCostRevisionRepository(self.quotation_service._session)
            cost_revision = await cost_repo.get_approved_cost(tenant_id, material_id)
        
        if cost_revision:
            return PricingDecision(
                material_id=material_id,
                supplier_id=supplier_id,
                suggested_price=cost_revision.requested_cost,
                level_number=5,
                pricing_source="STANDARD_COST",
                confidence_level="LOW",
                rationale=f"Approved standard cost revision #{cost_revision.id}",
            )
        
        # Priority 6: Manual (no suggestion) - return None to signal no pricing available
        return None
    
    async def get_pricing_suggestions(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> Optional['PricingDecision']:
        """
        Get pricing suggestions using 6-level hierarchy fallback logic.
        
        Alias for calculate_pricing() to match HTTP route expectations.
        
        Args:
            tenant_id: Tenant context
            material_id: Material being evaluated
            supplier_id: Supplier being evaluated
        
        Returns:
            PricingDecision with suggested price, or None if no pricing available
        """
        return await self.calculate_pricing(tenant_id, material_id, supplier_id)
    
    async def get_pricing_analysis(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get detailed pricing analysis across all 6 levels for a PO line.
        
        Useful for pricing transparency and decision-making.
        
        Args:
            tenant_id: Tenant context
            material_id: Material being evaluated
            supplier_id: Supplier being evaluated
        
        Returns:
            Dictionary with analysis across all 6 priority levels
        """
        analysis = {
            "material_id": str(material_id),
            "supplier_id": str(supplier_id),
            "priorities": [],
            "recommended_decision": None,
        }
        
        # Priority 1: Agreement
        agreement = None
        if hasattr(self.quotation_service, '_session'):
            agreement_repo = SupplierPriceAgreementRepository(self.quotation_service._session)
            agreement = await agreement_repo.get_active_by_supplier_material(
                tenant_id, supplier_id, material_id
            )
        
        if agreement and agreement.status == "ACTIVE":
            analysis["priorities"].append({
                "level": 1,
                "source": "SUPPLIER_AGREEMENT",
                "price": float(agreement.base_price),
                "status": "AVAILABLE",
            })
        else:
            analysis["priorities"].append({
                "level": 1,
                "source": "SUPPLIER_AGREEMENT",
                "price": None,
                "status": "NOT_AVAILABLE",
            })
        
        # Priority 2: Quotation
        quotation = await self.quotation_service.lookup_by_supplier_and_material(
            tenant_id, supplier_id, material_id
        )
        analysis["priorities"].append({
            "level": 2,
            "source": "QUOTATION",
            "price": float(quotation.unit_price) if quotation.found else None,
            "status": "AVAILABLE" if quotation.found else "NOT_AVAILABLE",
            "quotation_number": quotation.quotation_number if quotation.found else None,
        })
        
        # Priority 3: Same supplier history
        same_supplier = await self.same_supplier_service.lookup_by_supplier_and_material(
            tenant_id, supplier_id, material_id
        )
        analysis["priorities"].append({
            "level": 3,
            "source": "PURCHASE_HISTORY",
            "price": float(same_supplier.unit_price) if same_supplier.found else None,
            "status": "AVAILABLE" if same_supplier.found else "NOT_AVAILABLE",
            "purchase_count": same_supplier.purchase_count if same_supplier.found else 0,
        })
        
        # Priority 4: Any supplier history
        any_supplier = await self.any_supplier_service.lookup_latest_purchase_any_supplier(
            tenant_id, material_id
        )
        analysis["priorities"].append({
            "level": 4,
            "source": "BENCHMARK_ANY_SUPPLIER",
            "price": float(any_supplier.unit_price) if any_supplier.found else None,
            "status": "AVAILABLE" if any_supplier.found else "NOT_AVAILABLE",
            "supplier_count": any_supplier.total_suppliers if any_supplier.found else 0,
            "best_price": float(any_supplier.best_price) if any_supplier.found and any_supplier.best_price else None,
        })
        
        # Priority 5: Standard cost
        cost = None
        if hasattr(self.quotation_service, '_session'):
            cost_repo = StandardCostRevisionRepository(self.quotation_service._session)
            cost = await cost_repo.get_approved_cost(tenant_id, material_id)
        
        analysis["priorities"].append({
            "level": 5,
            "source": "STANDARD_COST",
            "price": float(cost.requested_cost) if cost else None,
            "status": "AVAILABLE" if cost else "NOT_AVAILABLE",
        })
        
        # Priority 6: Manual
        analysis["priorities"].append({
            "level": 6,
            "source": "MANUAL",
            "price": None,
            "status": "FALLBACK",
        })
        
        # Get recommended decision
        decision = await self.calculate_pricing(tenant_id, material_id, supplier_id)
        if decision:
            analysis["recommended_decision"] = decision.to_dict()
        
        return analysis
