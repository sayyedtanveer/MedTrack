"""
Price override tracking service for PO lines (Priority 2.5).

This service records when a user overrides the suggested price from the 6-level pricing engine.
Overrides are audit-logged for compliance and analysis of pricing decisions.

Use cases:
1. User saves PO line with price different from engine suggestion → record override
2. Query override history for a material/supplier → understand pricing patterns
3. Analyze override frequency → identify pricing policy deviations
4. Support procurement analysis → why did this supplier's price change?
"""
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.procurement_pricing_models import (
    PriceOverrideRecordModel,
)
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderLineModel,
)


@dataclass
class PriceOverrideRecord:
    """Record of a price override."""
    
    id: uuid.UUID
    material_id: uuid.UUID
    supplier_id: uuid.UUID
    
    # Suggested vs actual
    original_suggested_price: Optional[Decimal]  # Renamed from suggested_price
    override_price: Decimal
    override_reason: Optional[str]
    override_source: Optional[str]  # Renamed from suggested_source
    
    # Metrics
    variance_percent: Optional[Decimal]  # Renamed from price_variance_pct - (override - suggested) / suggested * 100
    
    # Audit
    overridden_by: uuid.UUID  # user_id
    created_at: datetime  # Renamed from overridden_at
    is_deleted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "material_id": str(self.material_id),
            "supplier_id": str(self.supplier_id),
            "original_suggested_price": float(self.original_suggested_price) if self.original_suggested_price else None,
            "override_price": float(self.override_price),
            "override_reason": self.override_reason,
            "override_source": self.override_source,
            "variance_percent": float(self.variance_percent) if self.variance_percent else None,
            "overridden_by": str(self.overridden_by),
            "created_at": self.created_at.isoformat(),
        }


class PriceOverrideService:
    """
    Service for recording and analyzing price overrides on PO lines.
    
    When a user saves a PO line with a price different from what the pricing
    engine suggested, this service records the override for audit and analysis.
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def record_override(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        supplier_id: uuid.UUID,
        original_suggested_price: Optional[Decimal],  # Renamed from suggested_price
        override_price: Decimal,
        override_reason: Optional[str],
        override_source: Optional[str],  # Renamed from suggested_source
        overridden_by: uuid.UUID,
    ) -> PriceOverrideRecord:
        """
        Record a price override when a user enters a price different from suggestion.
        
        Args:
            tenant_id: Tenant context
            material_id: Material being ordered
            supplier_id: Supplier being ordered from
            original_suggested_price: Price suggested by the 6-level engine (can be None for manual)
            override_price: Actual price user entered
            override_reason: Optional reason for override (e.g., "Volume discount", "Strategic relationship")
            override_source: Source of suggestion ("SUPPLIER_AGREEMENT", "QUOTATION", "PURCHASE_HISTORY", etc.)
            overridden_by: User ID of person making override
        
        Returns:
            PriceOverrideRecord with calculated variance
        """
        # Calculate variance percentage
        if original_suggested_price and original_suggested_price > 0:
            variance_pct = ((override_price - original_suggested_price) / original_suggested_price) * Decimal("100")
        else:
            variance_pct = Decimal("0") if not original_suggested_price else None
        
        # Create record in database
        override_record = PriceOverrideRecordModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            material_id=material_id,
            supplier_id=supplier_id,
            original_suggested_price=float(original_suggested_price) if original_suggested_price else None,
            override_price=float(override_price),
            override_reason=override_reason,
            override_source=override_source,
            variance_percent=float(variance_pct) if variance_pct else 0,
            overridden_by=overridden_by,
            is_deleted=False,
            created_by=overridden_by,
        )
        self._session.add(override_record)
        await self._session.flush()
        
        return PriceOverrideRecord(
            id=override_record.id,
            material_id=material_id,
            supplier_id=supplier_id,
            original_suggested_price=original_suggested_price,
            override_price=override_price,
            override_reason=override_reason,
            override_source=override_source,
            variance_percent=variance_pct if variance_pct is not None else Decimal("0"),
            overridden_by=overridden_by,
            created_at=override_record.created_at,
        )
    
    async def get_override_history_for_material_supplier(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        supplier_id: uuid.UUID,
        limit: int = 10,
    ) -> List[PriceOverrideRecord]:
        """
        Get override history for a material/supplier combination.
        
        Useful for understanding pricing patterns and deviations.
        
        Args:
            tenant_id: Tenant context
            material_id: Material to analyze
            supplier_id: Supplier to analyze
            limit: Maximum records to return (default 10, latest first)
        
        Returns:
            List of PriceOverrideRecord ordered by created_at DESC
        """
        stmt = (
            select(
                PriceOverrideRecordModel.id,
                PriceOverrideRecordModel.original_suggested_price,
                PriceOverrideRecordModel.override_price,
                PriceOverrideRecordModel.override_reason,
                PriceOverrideRecordModel.override_source,
                PriceOverrideRecordModel.variance_percent,
                PriceOverrideRecordModel.overridden_by,
                PriceOverrideRecordModel.created_at,
            )
            .where(
                and_(
                    PriceOverrideRecordModel.tenant_id == tenant_id,
                    PriceOverrideRecordModel.material_id == material_id,
                    PriceOverrideRecordModel.supplier_id == supplier_id,
                    PriceOverrideRecordModel.is_deleted == False,
                )
            )
            .order_by(PriceOverrideRecordModel.created_at.desc())
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        rows = result.all()
        
        records = []
        for row in rows:
            records.append(
                PriceOverrideRecord(
                    id=row[0],
                    material_id=material_id,
                    supplier_id=supplier_id,
                    original_suggested_price=Decimal(str(row[1])) if row[1] else None,
                    override_price=Decimal(str(row[2])),
                    override_reason=row[3],
                    override_source=row[4],
                    variance_percent=Decimal(str(row[5])) if row[5] else None,
                    overridden_by=row[6],
                    created_at=row[7],
                )
            )
        
        return records
    
    async def get_override_statistics(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get statistics about overrides for a material/supplier.
        
        Returns metrics like: override count, avg price, min/max price, etc.
        
        Args:
            tenant_id: Tenant context
            material_id: Material to analyze
            supplier_id: Supplier to analyze
        
        Returns:
            Dictionary with statistics
        """
        records = await self.get_override_history_for_material_supplier(
            tenant_id, material_id, supplier_id, limit=1000
        )
        
        if not records:
            return {
                "material_id": str(material_id),
                "supplier_id": str(supplier_id),
                "total_overrides": 0,
            }
        
        override_prices = [r.override_price for r in records]
        
        return {
            "material_id": str(material_id),
            "supplier_id": str(supplier_id),
            "total_overrides": len(records),
            "average_override_price": float(sum(override_prices) / len(override_prices)) if override_prices else 0,
            "min_override_price": float(min(override_prices)) if override_prices else None,
            "max_override_price": float(max(override_prices)) if override_prices else None,
        }
    
    async def analyze_override_trends(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        supplier_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Analyze override trends for a specific material/supplier.
        
        Returns information about pricing trends and patterns.
        
        Args:
            tenant_id: Tenant context
            material_id: Material to analyze
            supplier_id: Supplier to analyze
        
        Returns:
            Dictionary with trend information
        """
        records = await self.get_override_history_for_material_supplier(
            tenant_id, material_id, supplier_id, limit=1000
        )
        
        if not records:
            return {
                "material_id": str(material_id),
                "supplier_id": str(supplier_id),
                "trend_direction": "INSUFFICIENT_DATA",
                "total_records_analyzed": 0,
            }
        
        # Calculate trend direction based on override prices over time
        override_prices = [r.override_price for r in records]
        
        if len(override_prices) < 3:
            trend_direction = "INSUFFICIENT_DATA"
        else:
            # Compare oldest vs newest override prices (records are sorted DESC by created_at, so reverse)
            oldest_price = override_prices[-1]
            newest_price = override_prices[0]
            
            if newest_price > oldest_price:
                trend_direction = "UPWARD"
            elif newest_price < oldest_price:
                trend_direction = "DOWNWARD"
            else:
                trend_direction = "STABLE"
        
        return {
            "material_id": str(material_id),
            "supplier_id": str(supplier_id),
            "trend_direction": trend_direction,
            "total_records_analyzed": len(records),
            "average_override_price": float(sum(override_prices) / len(override_prices)) if override_prices else 0,
            "min_override_price": float(min(override_prices)) if override_prices else None,
            "max_override_price": float(max(override_prices)) if override_prices else None,
        }


