import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func

from backend.app.infrastructure.persistence.models.grn_model import GoodsReceiptNoteModel, GRNLineModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel

class PurchaseHistoryQueryService:
    def __init__(self, session):
        self._session = session

    async def get_purchasing_summary(self, material_id: uuid.UUID, tenant_id: uuid.UUID) -> Dict[str, Any]:
        # 1. Fetch latest completed GRN line details (status = "received", is_deleted = False)
        # Ordered by receipt date DESC, then creation date DESC
        latest_stmt = (
            select(
                GRNLineModel.unit_price,
                GoodsReceiptNoteModel.actual_receipt_date,
                SupplierModel.name.label("supplier_name"),
                SupplierModel.id.label("supplier_id")
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .join(SupplierModel, SupplierModel.id == GoodsReceiptNoteModel.supplier_id)
            .where(
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GRNLineModel.material_id == material_id,
                GoodsReceiptNoteModel.status == "received",
                GoodsReceiptNoteModel.is_deleted.is_(False),
                GRNLineModel.is_deleted.is_(False),
            )
            .order_by(
                GoodsReceiptNoteModel.actual_receipt_date.desc(),
                GoodsReceiptNoteModel.created_at.desc()
            )
            .limit(1)
        )
        latest_res = (await self._session.execute(latest_stmt)).first()

        # 2. Fetch purchase count (completed GRN lines count only)
        count_stmt = (
            select(func.count(GRNLineModel.id))
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .where(
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GRNLineModel.material_id == material_id,
                GoodsReceiptNoteModel.status == "received",
                GoodsReceiptNoteModel.is_deleted.is_(False),
                GRNLineModel.is_deleted.is_(False),
            )
        )
        purchase_count = (await self._session.execute(count_stmt)).scalar() or 0

        if latest_res:
            return {
                "latest_purchase_price": Decimal(str(latest_res[0])),
                "last_purchase_date": latest_res[1],
                "last_supplier_name": latest_res[2],
                "last_supplier_id": latest_res[3],
                "purchase_count": purchase_count
            }
        else:
            return {
                "latest_purchase_price": None,
                "last_purchase_date": None,
                "last_supplier_name": None,
                "last_supplier_id": None,
                "purchase_count": 0
            }

    async def get_purchase_history(
        self, material_id: uuid.UUID, tenant_id: uuid.UUID, page: int = 1, page_size: int = 25
    ) -> Dict[str, Any]:
        # Get tenant currency code (e.g. INR / USD)
        tenant_stmt = select(TenantModel.currency_code).where(TenantModel.id == tenant_id)
        currency_code = (await self._session.execute(tenant_stmt)).scalar() or "INR"

        # Count total rows for pagination (completed receipts only)
        total_stmt = (
            select(func.count(GRNLineModel.id))
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .where(
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GRNLineModel.material_id == material_id,
                GoodsReceiptNoteModel.status == "received",
                GoodsReceiptNoteModel.is_deleted.is_(False),
                GRNLineModel.is_deleted.is_(False)
            )
        )
        total = (await self._session.execute(total_stmt)).scalar() or 0

        # Query purchase history items (completed only, i.e. status = "received")
        offset = (page - 1) * page_size
        stmt = (
            select(
                GoodsReceiptNoteModel.actual_receipt_date.label("date"),
                SupplierModel.id.label("supplier_id"),
                SupplierModel.name.label("supplier_name"),
                PurchaseOrderModel.po_number.label("po_number"),
                GoodsReceiptNoteModel.grn_number.label("grn_number"),
                GRNLineModel.received_quantity.label("quantity"),
                UnitOfMeasureModel.code.label("uom_code"),
                GRNLineModel.unit_price.label("unit_price"),
            )
            .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
            .join(SupplierModel, SupplierModel.id == GoodsReceiptNoteModel.supplier_id)
            .join(PurchaseOrderModel, PurchaseOrderModel.id == GoodsReceiptNoteModel.purchase_order_id)
            .join(MaterialModel, MaterialModel.id == GRNLineModel.material_id)
            .join(UnitOfMeasureModel, UnitOfMeasureModel.id == MaterialModel.base_unit_id, isouter=True)
            .where(
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GRNLineModel.material_id == material_id,
                GoodsReceiptNoteModel.status == "received",
                GoodsReceiptNoteModel.is_deleted.is_(False),
                GRNLineModel.is_deleted.is_(False)
            )
            .order_by(
                GoodsReceiptNoteModel.actual_receipt_date.desc(),
                GoodsReceiptNoteModel.created_at.desc()
            )
            .offset(offset)
            .limit(page_size)
        )

        res = await self._session.execute(stmt)
        rows = res.all()

        history = []
        for row in rows:
            qty = float(row.quantity)
            price = float(row.unit_price)
            history.append({
                "date": row.date.date().isoformat() if hasattr(row.date, 'date') else (row.date.isoformat() if row.date else None),
                "supplier_id": row.supplier_id,
                "supplier_name": row.supplier_name,
                "po_number": row.po_number,
                "grn_number": row.grn_number,
                "quantity": qty,
                "uom": row.uom_code or "",
                "unit_price": price,
                "total_value": qty * price,
                "currency": currency_code,
            })
        return {
            "items": history,
            "total": total,
            "page": page,
            "page_size": page_size
        }
