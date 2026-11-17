"""
Supplier quotation lookup service for 6-level PO pricing engine.

This service provides quotation lookups as Priority 2 of the 6-level pricing hierarchy:
1. Active supplier agreement (Priority 1)
2. **Approved supplier quotation (Priority 2) ← This service**
3. Latest purchase (same supplier, Priority 3)
4. Latest purchase (any supplier, Priority 4)
5. Approved standard cost (Priority 5)
6. Manual (Priority 6)

The quotation lookup searches for approved/awarded quotations for a material from a supplier
and returns the best match with metadata for frontend display and audit trails.
"""
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.quality_model import SupplierQuotationModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.rfq_model import RFQModel


class QuotationLookupResult:
    """Result from supplier quotation lookup."""
    
    def __init__(
        self,
        found: bool,
        quotation_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None,
        quotation_number: Optional[str] = None,
        unit_price: Optional[Decimal] = None,
        quantity: Optional[Decimal] = None,
        valid_until: Optional[datetime] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,  # "approved_quotation" for this priority
        rfq_number: Optional[str] = None,
    ):
        self.found = found
        self.quotation_id = quotation_id
        self.supplier_id = supplier_id
        self.quotation_number = quotation_number
        self.unit_price = unit_price
        self.quantity = quantity
        self.valid_until = valid_until
        self.status = status
        self.source = source
        self.rfq_number = rfq_number
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "found": self.found,
            "quotation_id": str(self.quotation_id) if self.quotation_id else None,
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "quotation_number": self.quotation_number,
            "unit_price": float(self.unit_price) if self.unit_price else None,
            "quantity": float(self.quantity) if self.quantity else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "status": self.status,
            "source": self.source,
            "rfq_number": self.rfq_number,
        }


class SupplierQuotationLookupService:
    """
    Service for looking up supplier quotations for PO pricing.
    
    Searches for approved or awarded quotations for a material from a specific supplier.
    Returns the best match (latest, valid, non-expired quotation).
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def lookup_by_supplier_and_material(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> QuotationLookupResult:
        """
        Look up an approved supplier quotation for a material from a specific supplier.
        
        Search criteria:
        - Status: APPROVED or AWARDED (actively usable)
        - valid_until: NULL or future date (not expired)
        - Ordered by: Latest created_at DESC (most recent quotation)
        
        Args:
            tenant_id: Tenant context
            supplier_id: Supplier to search
            material_id: Material to search
        
        Returns:
            QuotationLookupResult with quotation data or found=False if not found
        """
        stmt = (
            select(SupplierQuotationModel)
            .where(
                and_(
                    SupplierQuotationModel.tenant_id == tenant_id,
                    SupplierQuotationModel.supplier_id == supplier_id,
                    SupplierQuotationModel.material_id == material_id,
                    SupplierQuotationModel.status.in_(["APPROVED", "AWARDED"]),
                    SupplierQuotationModel.is_deleted == False,
                )
            )
            .order_by(SupplierQuotationModel.created_at.desc())
        )
        
        result = await self._session.execute(stmt)
        quotation = result.scalars().first()
        
        if not quotation:
            return QuotationLookupResult(found=False)
        
        # Check if quotation is expired
        if quotation.valid_until and quotation.valid_until < datetime.now(timezone.utc).date():
            # Expired but found, return with metadata
            return QuotationLookupResult(
                found=False,  # Expired quotations are not usable
                quotation_id=quotation.id,
                quotation_number=quotation.quotation_number,
                unit_price=Decimal(str(quotation.unit_price)),
                quantity=Decimal(str(quotation.quantity)),
                valid_until=quotation.valid_until,
                status=quotation.status,
                source="approved_quotation_expired",
            )
        
        # Get RFQ number if linked via purchase_order
        rfq_number = None
        if quotation.purchase_order_id:
            rfq_stmt = (
                select(RFQModel.rfq_number)
                .where(RFQModel.awarded_po_id == quotation.purchase_order_id)
                .limit(1)
            )
            rfq_result = await self._session.execute(rfq_stmt)
            rfq_number = rfq_result.scalar()
        
        return QuotationLookupResult(
            found=True,
            quotation_id=quotation.id,
            supplier_id=quotation.supplier_id,
            quotation_number=quotation.quotation_number,
            unit_price=Decimal(str(quotation.unit_price)),
            quantity=Decimal(str(quotation.quantity)),
            valid_until=quotation.valid_until,
            status=quotation.status,
            source="approved_quotation",
            rfq_number=rfq_number,
        )
    
    async def lookup_latest_by_supplier_and_material(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        material_id: uuid.UUID,
        include_expired: bool = False,
    ) -> QuotationLookupResult:
        """
        Look up the latest supplier quotation for a material from a supplier.
        
        Useful for reference pricing when approved quotations don't exist.
        Can optionally include expired quotations for historical reference.
        
        Args:
            tenant_id: Tenant context
            supplier_id: Supplier to search
            material_id: Material to search
            include_expired: If True, include expired quotations in results
        
        Returns:
            QuotationLookupResult with latest quotation or found=False
        """
        stmt = (
            select(SupplierQuotationModel)
            .where(
                and_(
                    SupplierQuotationModel.tenant_id == tenant_id,
                    SupplierQuotationModel.supplier_id == supplier_id,
                    SupplierQuotationModel.material_id == material_id,
                    SupplierQuotationModel.is_deleted == False,
                )
            )
            .order_by(SupplierQuotationModel.created_at.desc())
            .limit(1)
        )
        
        result = await self._session.execute(stmt)
        quotation = result.scalars().first()
        
        if not quotation:
            return QuotationLookupResult(found=False)
        
        # Check expiration
        is_expired = (
            quotation.valid_until
            and quotation.valid_until < datetime.now(timezone.utc).date()
        )
        
        if is_expired and not include_expired:
            return QuotationLookupResult(found=False)
        
        source = "approved_quotation"
        if not quotation.status in ["APPROVED", "AWARDED"]:
            source = f"quotation_{quotation.status.lower()}"
        if is_expired:
            source += "_expired"
        
        return QuotationLookupResult(
            found=True,
            quotation_id=quotation.id,
            supplier_id=quotation.supplier_id,
            quotation_number=quotation.quotation_number,
            unit_price=Decimal(str(quotation.unit_price)),
            quantity=Decimal(str(quotation.quantity)),
            valid_until=quotation.valid_until,
            status=quotation.status,
            source=source,
        )
    
    async def lookup_all_approved_by_material(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> list[QuotationLookupResult]:
        """
        Look up all approved quotations for a material from all suppliers.
        
        Useful for comparison shopping or RFQ response analysis.
        Returns list sorted by unit_price ASC (best price first).
        
        Args:
            tenant_id: Tenant context
            material_id: Material to search
        
        Returns:
            List of QuotationLookupResult (found=True only), ordered by price
        """
        stmt = (
            select(SupplierQuotationModel)
            .where(
                and_(
                    SupplierQuotationModel.tenant_id == tenant_id,
                    SupplierQuotationModel.material_id == material_id,
                    SupplierQuotationModel.status.in_(["APPROVED", "AWARDED"]),
                    SupplierQuotationModel.is_deleted == False,
                )
            )
            .order_by(SupplierQuotationModel.unit_price.asc())
        )
        
        result = await self._session.execute(stmt)
        quotations = result.scalars().all()
        
        results = []
        now = datetime.now(timezone.utc).date()
        
        for quotation in quotations:
            # Skip expired quotations
            if quotation.valid_until and quotation.valid_until < now:
                continue
            
            results.append(
                QuotationLookupResult(
                    found=True,
                    quotation_id=quotation.id,
                    supplier_id=quotation.supplier_id,
                    quotation_number=quotation.quotation_number,
                    unit_price=Decimal(str(quotation.unit_price)),
                    quantity=Decimal(str(quotation.quantity)),
                    valid_until=quotation.valid_until,
                    status=quotation.status,
                    source="approved_quotation",
                )
            )
        
        return results
