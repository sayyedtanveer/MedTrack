"""
Purchase history lookup service for 6-level PO pricing engine.

This service provides purchase history lookups for the 6-level pricing hierarchy:
1. Active supplier agreement (Priority 1)
2. Approved supplier quotation (Priority 2)
3. **Latest purchase (same supplier, Priority 3) ← This service**
4. Latest purchase (any supplier, Priority 4)
5. Approved standard cost (Priority 5)
6. Manual (Priority 6)

The service queries completed GRN lines (goods receipt notes) to find historical
purchase prices from specific suppliers. This helps establish baseline pricing when
quotations or agreements are not available.
"""
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.grn_model import (
    GoodsReceiptNoteModel,
    GRNLineModel,
)
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel


class PurchaseHistoryResult:
    """Result from purchase history lookup."""
    
    def __init__(
        self,
        found: bool,
        material_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None,
        unit_price: Optional[Decimal] = None,
        quantity: Optional[Decimal] = None,
        receipt_date: Optional[date] = None,
        grn_number: Optional[str] = None,
        po_number: Optional[str] = None,
        source: Optional[str] = None,  # "same_supplier_history" or "any_supplier_history"
        purchase_count: int = 0,  # Total purchases from this supplier
    ):
        self.found = found
        self.material_id = material_id
        self.supplier_id = supplier_id
        self.unit_price = unit_price
        self.quantity = quantity
        self.receipt_date = receipt_date
        self.grn_number = grn_number
        self.po_number = po_number
        self.source = source
        self.purchase_count = purchase_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "found": self.found,
            "material_id": str(self.material_id) if self.material_id else None,
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "unit_price": float(self.unit_price) if self.unit_price else None,
            "quantity": float(self.quantity) if self.quantity else None,
            "receipt_date": self.receipt_date.isoformat() if self.receipt_date else None,
            "grn_number": self.grn_number,
            "po_number": self.po_number,
            "source": self.source,
            "purchase_count": self.purchase_count,
        }


class PurchaseHistoryLookupService:
    """
    Service for looking up purchase history for PO pricing.
    
    Searches completed GRN lines (received goods) to find historical purchase prices.
    Used when supplier agreements or quotations are not available.
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def lookup_by_supplier_and_material(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> PurchaseHistoryResult:
        """
        Look up latest purchase history for a material from a specific supplier.
        
        Search criteria:
        - GRN Status: "received" or "inspected" (completed receipts only)
        - Supplier: specific supplier ID
        - Material: specific material ID
        - Ordered by: Latest actual_receipt_date DESC (most recent purchase)
        
        Args:
            tenant_id: Tenant context
            supplier_id: Supplier to search
            material_id: Material to search
        
        Returns:
            PurchaseHistoryResult with purchase data or found=False if not found
        """
        stmt = (
            select(
                GRNLineModel.unit_price,
                GRNLineModel.received_quantity,
                GoodsReceiptNoteModel.actual_receipt_date,
                GoodsReceiptNoteModel.grn_number,
                PurchaseOrderModel.po_number,
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .join(
                PurchaseOrderModel,
                PurchaseOrderModel.id == GoodsReceiptNoteModel.purchase_order_id,
            )
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    PurchaseOrderModel.tenant_id == tenant_id,
                    GoodsReceiptNoteModel.supplier_id == supplier_id,
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
                    PurchaseOrderModel.is_deleted == False,
                )
            )
            .order_by(
                GoodsReceiptNoteModel.actual_receipt_date.desc(),
                GoodsReceiptNoteModel.created_at.desc(),
            )
            .limit(1)
        )
        
        result = await self._session.execute(stmt)
        row = result.first()
        
        if not row:
            return PurchaseHistoryResult(found=False)
        
        # Count total purchases from this supplier for this material
        count_stmt = (
            select(func.count(GRNLineModel.id))
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    GoodsReceiptNoteModel.supplier_id == supplier_id,
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
                )
            )
        )
        count_result = await self._session.execute(count_stmt)
        purchase_count = count_result.scalar() or 0
        
        return PurchaseHistoryResult(
            found=True,
            material_id=material_id,
            supplier_id=supplier_id,
            unit_price=Decimal(str(row[0])),
            quantity=Decimal(str(row[1])),
            receipt_date=row[2].date() if row[2] else None,
            grn_number=row[3],
            po_number=row[4],
            source="same_supplier_history",
            purchase_count=purchase_count,
        )
    
    async def get_purchase_summary_by_supplier_and_material(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get comprehensive purchase summary for a material from a supplier.
        
        Includes latest price, count, average price, min/max prices, and date range.
        
        Args:
            tenant_id: Tenant context
            supplier_id: Supplier to search
            material_id: Material to search
        
        Returns:
            Dictionary with latest_price, purchase_count, avg_price, min_price, max_price,
            earliest_receipt_date, latest_receipt_date
        """
        stmt = (
            select(
                GRNLineModel.unit_price,
                GoodsReceiptNoteModel.actual_receipt_date,
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    GoodsReceiptNoteModel.supplier_id == supplier_id,
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
                )
            )
            .order_by(GoodsReceiptNoteModel.actual_receipt_date.desc())
        )
        
        result = await self._session.execute(stmt)
        rows = result.all()
        
        if not rows:
            return {
                "found": False,
                "supplier_id": str(supplier_id),
                "material_id": str(material_id),
                "purchase_count": 0,
            }
        
        prices = [Decimal(str(row[0])) for row in rows]
        latest_price = prices[0]
        purchase_count = len(prices)
        avg_price = sum(prices) / Decimal(str(purchase_count))
        min_price = min(prices)
        max_price = max(prices)
        
        # Get earliest and latest dates
        dates = [row[1].date() if row[1] else None for row in rows]
        earliest_date = min([d for d in dates if d is not None]) if any(dates) else None
        latest_date = max([d for d in dates if d is not None]) if any(dates) else None
        
        return {
            "found": True,
            "supplier_id": str(supplier_id),
            "material_id": str(material_id),
            "latest_price": float(latest_price),
            "purchase_count": purchase_count,
            "avg_price": float(avg_price),
            "min_price": float(min_price),
            "max_price": float(max_price),
            "earliest_receipt_date": earliest_date.isoformat() if earliest_date else None,
            "latest_receipt_date": latest_date.isoformat() if latest_date else None,
            "price_trend": self._calculate_price_trend(prices),
        }
    
    @staticmethod
    def _calculate_price_trend(prices: list[Decimal]) -> str:
        """
        Calculate price trend: "stable", "increasing", "decreasing", "volatile".
        
        Args:
            prices: List of prices in reverse chronological order (newest first)
        
        Returns:
            Trend description
        """
        if len(prices) < 2:
            return "insufficient_data"
        
        # Compare last 3 prices to current
        recent_prices = prices[:min(3, len(prices))]
        older_prices = prices[min(3, len(prices)) :]
        
        if not older_prices:
            return "insufficient_data"
        
        recent_avg = sum(recent_prices) / len(recent_prices)
        older_avg = sum(older_prices) / len(older_prices)
        
        # Calculate percentage change
        change_pct = abs(recent_avg - older_avg) / older_avg * 100
        
        if change_pct < 2:
            return "stable"
        elif recent_avg > older_avg:
            return "increasing"
        else:
            return "decreasing"
