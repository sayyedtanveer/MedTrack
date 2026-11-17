"""
Any-supplier purchase history lookup service for 6-level PO pricing engine.

This service provides purchase history lookups across all suppliers for the 6-level pricing hierarchy:
1. Active supplier agreement (Priority 1)
2. Approved supplier quotation (Priority 2)
3. Latest purchase (same supplier, Priority 3)
4. **Latest purchase (any supplier, Priority 4) ← This service**
5. Approved standard cost (Priority 5)
6. Manual (Priority 6)

The service queries completed GRN lines (goods receipt notes) to find the latest historical
purchase price for a material from ANY supplier. This provides a fallback pricing reference
when the same supplier has no history but other suppliers do.
"""
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import date
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


class AnySupplierHistoryResult:
    """Result from any-supplier purchase history lookup."""
    
    def __init__(
        self,
        found: bool,
        material_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None,
        supplier_name: Optional[str] = None,
        unit_price: Optional[Decimal] = None,
        quantity: Optional[Decimal] = None,
        receipt_date: Optional[date] = None,
        grn_number: Optional[str] = None,
        po_number: Optional[str] = None,
        source: str = "any_supplier_history",
        total_suppliers: int = 0,  # How many suppliers have purchased this material
        best_price: Optional[Decimal] = None,  # Lowest price across all suppliers
        best_supplier_name: Optional[str] = None,
    ):
        self.found = found
        self.material_id = material_id
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name
        self.unit_price = unit_price
        self.quantity = quantity
        self.receipt_date = receipt_date
        self.grn_number = grn_number
        self.po_number = po_number
        self.source = source
        self.total_suppliers = total_suppliers
        self.best_price = best_price
        self.best_supplier_name = best_supplier_name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "found": self.found,
            "material_id": str(self.material_id) if self.material_id else None,
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "supplier_name": self.supplier_name,
            "unit_price": float(self.unit_price) if self.unit_price else None,
            "quantity": float(self.quantity) if self.quantity else None,
            "receipt_date": self.receipt_date.isoformat() if self.receipt_date else None,
            "grn_number": self.grn_number,
            "po_number": self.po_number,
            "source": self.source,
            "total_suppliers": self.total_suppliers,
            "best_price": float(self.best_price) if self.best_price else None,
            "best_supplier_name": self.best_supplier_name,
        }


class AnySupplierHistoryLookupService:
    """
    Service for looking up purchase history from any supplier for PO pricing.
    
    Searches completed GRN lines to find the latest purchase price for a material,
    regardless of supplier. Returns the most recent purchase plus metadata about
    the best price available across all suppliers.
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def lookup_latest_purchase_any_supplier(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> AnySupplierHistoryResult:
        """
        Look up the latest purchase of a material from ANY supplier.
        
        Search criteria:
        - GRN Status: "received" or "inspected" (completed receipts only)
        - Material: specific material ID
        - Supplier: any supplier
        - Ordered by: Latest actual_receipt_date DESC (most recent purchase)
        
        Args:
            tenant_id: Tenant context
            material_id: Material to search
        
        Returns:
            AnySupplierHistoryResult with latest purchase and best price metadata
        """
        # Get the latest purchase
        stmt = (
            select(
                GRNLineModel.unit_price,
                GRNLineModel.received_quantity,
                GoodsReceiptNoteModel.actual_receipt_date,
                GoodsReceiptNoteModel.grn_number,
                PurchaseOrderModel.po_number,
                GoodsReceiptNoteModel.supplier_id,
                SupplierModel.name.label("supplier_name"),
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .join(
                PurchaseOrderModel,
                PurchaseOrderModel.id == GoodsReceiptNoteModel.purchase_order_id,
            )
            .join(SupplierModel, SupplierModel.id == GoodsReceiptNoteModel.supplier_id)
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    PurchaseOrderModel.tenant_id == tenant_id,
                    PurchaseOrderModel.is_deleted.is_(False),
                    SupplierModel.tenant_id == tenant_id,
                    SupplierModel.is_deleted.is_(False),
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
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
            return AnySupplierHistoryResult(found=False)
        
        # Get metadata: count of suppliers and best price
        metadata = await self._get_material_purchase_metadata(tenant_id, material_id)
        
        return AnySupplierHistoryResult(
            found=True,
            material_id=material_id,
            supplier_id=row[5],
            supplier_name=row[6],
            unit_price=Decimal(str(row[0])),
            quantity=Decimal(str(row[1])),
            receipt_date=row[2].date() if row[2] else None,
            grn_number=row[3],
            po_number=row[4],
            source="any_supplier_history",
            total_suppliers=metadata["supplier_count"],
            best_price=metadata["best_price"],
            best_supplier_name=metadata["best_supplier_name"],
        )
    
    async def get_best_historical_price(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> AnySupplierHistoryResult:
        """
        Look up the LOWEST historical price for a material across all suppliers.
        
        Useful for benchmarking and finding best-in-class suppliers.
        
        Args:
            tenant_id: Tenant context
            material_id: Material to search
        
        Returns:
            AnySupplierHistoryResult with best price purchase details
        """
        stmt = (
            select(
                GRNLineModel.unit_price,
                GRNLineModel.received_quantity,
                GoodsReceiptNoteModel.actual_receipt_date,
                GoodsReceiptNoteModel.grn_number,
                PurchaseOrderModel.po_number,
                GoodsReceiptNoteModel.supplier_id,
                SupplierModel.name.label("supplier_name"),
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .join(
                PurchaseOrderModel,
                PurchaseOrderModel.id == GoodsReceiptNoteModel.purchase_order_id,
            )
            .join(SupplierModel, SupplierModel.id == GoodsReceiptNoteModel.supplier_id)
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    PurchaseOrderModel.tenant_id == tenant_id,
                    PurchaseOrderModel.is_deleted.is_(False),
                    SupplierModel.tenant_id == tenant_id,
                    SupplierModel.is_deleted.is_(False),
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
                )
            )
            .order_by(GRNLineModel.unit_price.asc())  # Lowest price first
            .limit(1)
        )
        
        result = await self._session.execute(stmt)
        row = result.first()
        
        if not row:
            return AnySupplierHistoryResult(found=False)
        
        metadata = await self._get_material_purchase_metadata(tenant_id, material_id)
        
        return AnySupplierHistoryResult(
            found=True,
            material_id=material_id,
            supplier_id=row[5],
            supplier_name=row[6],
            unit_price=Decimal(str(row[0])),
            quantity=Decimal(str(row[1])),
            receipt_date=row[2].date() if row[2] else None,
            grn_number=row[3],
            po_number=row[4],
            source="any_supplier_best_price",
            total_suppliers=metadata["supplier_count"],
            best_price=metadata["best_price"],
            best_supplier_name=metadata["best_supplier_name"],
        )
    
    async def get_supplier_comparison_for_material(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get comparison of all suppliers' historical prices for a material.
        
        Returns sorted list by unit_price ASC for benchmarking.
        
        Args:
            tenant_id: Tenant context
            material_id: Material to search
        
        Returns:
            Dictionary with supplier_count, comparisons list, and pricing stats
        """
        stmt = (
            select(
                GoodsReceiptNoteModel.supplier_id,
                SupplierModel.name.label("supplier_name"),
                func.min(GRNLineModel.unit_price).label("min_price"),
                func.max(GRNLineModel.unit_price).label("max_price"),
                func.avg(GRNLineModel.unit_price).label("avg_price"),
                func.count(GRNLineModel.id).label("purchase_count"),
                func.max(GoodsReceiptNoteModel.actual_receipt_date).label("latest_receipt"),
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .join(SupplierModel, SupplierModel.id == GoodsReceiptNoteModel.supplier_id)
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    SupplierModel.tenant_id == tenant_id,
                    SupplierModel.is_deleted.is_(False),
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
                )
            )
            .group_by(GoodsReceiptNoteModel.supplier_id, SupplierModel.name)
            .order_by(func.min(GRNLineModel.unit_price).asc())
        )
        
        result = await self._session.execute(stmt)
        rows = result.all()
        
        if not rows:
            return {
                "found": False,
                "material_id": str(material_id),
                "supplier_count": 0,
                "comparisons": [],
            }
        
        comparisons = []
        prices = []
        
        for row in rows:
            min_price = Decimal(str(row[2]))
            avg_price = Decimal(str(row[4]))
            prices.append(avg_price)
            
            comparisons.append({
                "supplier_id": str(row[0]),
                "supplier_name": row[1],
                "min_price": float(min_price),
                "max_price": float(row[3]),
                "avg_price": float(avg_price),
                "purchase_count": row[5],
                "latest_receipt": row[6].isoformat() if row[6] else None,
            })
        
        # Calculate overall stats
        if prices:
            overall_min = float(min(prices))
            overall_max = float(max(prices))
            overall_avg = float(sum(prices) / len(prices))
        else:
            overall_min = overall_max = overall_avg = None
        
        return {
            "found": True,
            "material_id": str(material_id),
            "supplier_count": len(rows),
            "comparisons": comparisons,
            "overall_stats": {
                "min_price": overall_min,
                "max_price": overall_max,
                "avg_price": overall_avg,
                "price_range": overall_max - overall_min if overall_min and overall_max else None,
            },
        }
    
    async def _get_material_purchase_metadata(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get metadata about purchases of a material: supplier count and best price.
        
        Args:
            tenant_id: Tenant context
            material_id: Material to analyze
        
        Returns:
            Dictionary with supplier_count, best_price, best_supplier_name
        """
        # Count suppliers
        supplier_count_stmt = (
            select(func.count(func.distinct(GoodsReceiptNoteModel.supplier_id)))
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
                )
            )
        )
        supplier_count = await self._session.execute(supplier_count_stmt)
        count = supplier_count.scalar() or 0
        
        # Get best price
        best_price_stmt = (
            select(
                func.min(GRNLineModel.unit_price),
                SupplierModel.name,
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .join(SupplierModel, SupplierModel.id == GoodsReceiptNoteModel.supplier_id)
            .where(
                and_(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GRNLineModel.tenant_id == tenant_id,
                    GRNLineModel.material_id == material_id,
                    GoodsReceiptNoteModel.status.in_(["received", "inspected"]),
                    GoodsReceiptNoteModel.is_deleted == False,
                    GRNLineModel.is_deleted == False,
                )
            )
            .group_by(SupplierModel.name)
            .order_by(func.min(GRNLineModel.unit_price).asc())
            .limit(1)
        )
        
        best_price_result = await self._session.execute(best_price_stmt)
        best_price_row = best_price_result.first()
        
        best_price = None
        best_supplier_name = None
        
        if best_price_row:
            best_price = Decimal(str(best_price_row[0]))
            best_supplier_name = best_price_row[1]
        
        return {
            "supplier_count": count,
            "best_price": best_price,
            "best_supplier_name": best_supplier_name,
        }
