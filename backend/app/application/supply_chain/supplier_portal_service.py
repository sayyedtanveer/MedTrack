from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.finance.finance_service import FinanceService
from backend.app.application.finance.notification_service import NotificationService
from backend.app.application.supply_chain.po_number_service import PONumberService
from backend.app.infrastructure.persistence.models.finance_models import (
    SupplierInvoiceModel,
    SupplierPaymentModel,
)
from backend.app.infrastructure.persistence.models.grn_model import GoodsReceiptNoteModel, GRNLineModel
from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderLineModel,
    PurchaseOrderModel,
)
from backend.app.infrastructure.persistence.models.quality_model import SupplierQuotationModel
from backend.app.infrastructure.persistence.models.rfq_model import RFQModel, RFQSupplierModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel


class SupplierPortalService:
    """Supplier-facing orchestration over existing procurement/finance models."""

    def __init__(self, session: AsyncSession, *, email_service=None, connection_manager=None) -> None:
        self.session = session
        self.email_service = email_service
        self.connection_manager = connection_manager

    async def get_profile(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> dict[str, Any]:
        supplier = await self._supplier_or_error(tenant_id, supplier_id)
        return self._supplier_to_dict(supplier)

    async def update_profile(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        supplier = await self._supplier_or_error(tenant_id, supplier_id)
        allowed = {"contact_person", "email", "phone", "address", "gst", "payment_terms"}
        changed: dict[str, Any] = {}
        before = self._supplier_to_dict(supplier)
        for key, value in payload.items():
            if key not in allowed:
                continue
            clean_value = value.strip() if isinstance(value, str) else value
            if getattr(supplier, key) != clean_value:
                setattr(supplier, key, clean_value)
                changed[key] = clean_value

        if changed:
            supplier.updated_by = user_id
            supplier.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(supplier)
            await self._notify_procurement(
                tenant_id,
                "SUPPLIER_PROFILE_UPDATED",
                f"Supplier {supplier.code} updated profile",
                f"{supplier.name} changed supplier profile information.",
                reference_type="supplier",
                reference_id=supplier.id,
            )
        return {**self._supplier_to_dict(supplier), "changed_fields": sorted(changed), "before": before}

    async def dashboard(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> dict[str, Any]:
        supplier = await self._supplier_or_error(tenant_id, supplier_id)
        po_by_status = await self._counts_by_status(PurchaseOrderModel, tenant_id, supplier_id)
        quotation_by_status = await self._counts_by_status(SupplierQuotationModel, tenant_id, supplier_id)
        invoice_by_status = await self._counts_by_status(SupplierInvoiceModel, tenant_id, supplier_id)

        outstanding = await self.session.scalar(
            select(func.coalesce(func.sum(SupplierInvoiceModel.grand_total - SupplierInvoiceModel.paid_amount), 0))
            .where(
                SupplierInvoiceModel.tenant_id == tenant_id,
                SupplierInvoiceModel.supplier_id == supplier_id,
                SupplierInvoiceModel.is_deleted.is_(False),
                SupplierInvoiceModel.status.in_(["PENDING", "PARTIAL", "OVERDUE"]),
            )
        )
        pending_receipts = await self.session.scalar(
            select(func.count(GoodsReceiptNoteModel.id)).where(
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GoodsReceiptNoteModel.supplier_id == supplier_id,
                GoodsReceiptNoteModel.status == "pending_receipt",
                GoodsReceiptNoteModel.is_deleted.is_(False),
            )
        )
        pending_rfqs = await self.session.scalar(
            select(func.count(RFQSupplierModel.id))
            .join(RFQModel, RFQModel.id == RFQSupplierModel.rfq_id)
            .where(
                RFQSupplierModel.tenant_id == tenant_id,
                RFQSupplierModel.supplier_id == supplier_id,
                RFQSupplierModel.status == "invited",
                RFQModel.status == "sent",
                RFQModel.is_deleted.is_(False),
            )
        )

        recent_pos = await self._recent_purchase_orders(tenant_id, supplier_id, limit=5)
        action_items = [
            {
                "type": "po_acknowledgement",
                "label": "Purchase orders waiting for acknowledgement",
                "count": po_by_status.get("sent", 0),
                "href": "/supplier-portal",
            },
            {
                "type": "rfq_response",
                "label": "RFQs waiting for quotation",
                "count": int(pending_rfqs or 0),
                "href": "/supplier-portal/quotations",
            },
            {
                "type": "shipment_notice",
                "label": "Shipments waiting for buyer receipt",
                "count": int(pending_receipts or 0),
                "href": "/supplier-portal/receipts",
            },
            {
                "type": "invoice_payment",
                "label": "Open invoice balance",
                "count": float(outstanding or 0),
                "href": "/supplier-portal/invoices",
            },
        ]

        return {
            "supplier": self._supplier_to_dict(supplier),
            "purchase_orders": {"by_status": po_by_status, "total": sum(po_by_status.values())},
            "quotations": {"by_status": quotation_by_status, "total": sum(quotation_by_status.values())},
            "invoices": {
                "by_status": invoice_by_status,
                "total": sum(invoice_by_status.values()),
                "outstanding": float(outstanding or 0),
            },
            "receipts": {"pending": int(pending_receipts or 0)},
            "performance": {"rating": float(supplier.performance_rating) if supplier.performance_rating is not None else None},
            "recent_purchase_orders": recent_pos,
            "action_items": action_items,
        }

    async def list_quotations(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(SupplierQuotationModel)
                .where(
                    SupplierQuotationModel.tenant_id == tenant_id,
                    SupplierQuotationModel.supplier_id == supplier_id,
                    SupplierQuotationModel.is_deleted.is_(False),
                )
                .order_by(SupplierQuotationModel.created_at.desc())
            )
        ).scalars().all()
        return [self._quotation_to_dict(row) for row in rows]

    async def get_quotation(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        quotation_id: uuid.UUID,
    ) -> dict[str, Any]:
        quotation = await self.session.get(SupplierQuotationModel, quotation_id)
        if (
            not quotation
            or quotation.tenant_id != tenant_id
            or quotation.supplier_id != supplier_id
            or quotation.is_deleted
        ):
            raise ValueError("Quotation not found")
        return self._quotation_to_dict(quotation)

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        query = select(SupplierInvoiceModel).where(
            SupplierInvoiceModel.tenant_id == tenant_id,
            SupplierInvoiceModel.supplier_id == supplier_id,
            SupplierInvoiceModel.is_deleted.is_(False),
        )
        if status:
            query = query.where(SupplierInvoiceModel.status == status)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = (
            await self.session.execute(
                query.order_by(SupplierInvoiceModel.invoice_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return {
            "items": [self._supplier_invoice_to_dict(row) for row in rows],
            "total": int(total or 0),
            "page": page,
            "pages": int(((total or 0) + page_size - 1) // page_size),
        }

    async def get_invoice(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID, invoice_id: uuid.UUID) -> dict[str, Any]:
        invoice = await self._supplier_invoice_or_error(tenant_id, supplier_id, invoice_id)
        return self._supplier_invoice_to_dict(invoice)

    async def create_invoice(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        po_id = payload.get("purchase_order_id")
        if po_id:
            po = await self._purchase_order_or_error(tenant_id, supplier_id, po_id)
            if po.status not in {"acknowledged", "partial", "received"}:
                raise ValueError("Supplier invoice can be submitted after PO acknowledgement or receipt")

        invoice = await FinanceService(self.session).create_supplier_invoice(
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_order_id=po_id,
            supplier_invoice_ref=payload.get("supplier_invoice_ref"),
            invoice_date=payload["invoice_date"],
            due_date=payload["due_date"],
            subtotal=float(payload["subtotal"]),
            tax_amount=float(payload.get("tax_amount") or 0),
            grand_total=float(payload["grand_total"]),
            created_by=user_id,
            notes=payload.get("notes"),
        )
        await self._notify_procurement(
            tenant_id,
            "SUPPLIER_INVOICE_SUBMITTED",
            f"Supplier invoice {invoice.invoice_number} submitted",
            f"{invoice.supplier_name} submitted an invoice for approval/payment.",
            reference_type="supplier_invoice",
            reference_id=invoice.id,
        )
        return self._supplier_invoice_to_dict(invoice)

    async def list_payments(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        query = select(SupplierPaymentModel).where(
            SupplierPaymentModel.tenant_id == tenant_id,
            SupplierPaymentModel.supplier_id == supplier_id,
        )
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = (
            await self.session.execute(
                query.order_by(SupplierPaymentModel.payment_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return {
            "items": [self._supplier_payment_to_dict(row) for row in rows],
            "total": int(total or 0),
            "page": page,
            "pages": int(((total or 0) + page_size - 1) // page_size),
        }

    async def list_receipts(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        query = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GoodsReceiptNoteModel.supplier_id == supplier_id,
                GoodsReceiptNoteModel.is_deleted.is_(False),
            )
        )
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = (
            await self.session.execute(
                query.order_by(GoodsReceiptNoteModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().unique().all()
        return {
            "items": [self._grn_to_dict(row) for row in rows],
            "total": int(total or 0),
            "page": page,
            "pages": int(((total or 0) + page_size - 1) // page_size),
        }

    async def create_shipping_notice(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        user_id: uuid.UUID,
        po_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        po = await self._purchase_order_or_error(tenant_id, supplier_id, po_id, with_lines=True)
        if po.status not in {"sent", "acknowledged", "partial"}:
            raise ValueError("PO is not open for shipment notice")
        if not payload.get("lines"):
            raise ValueError("At least one shipment line is required")

        grn_number = f"ASN-{await PONumberService(self.session).generate(tenant_id)}"
        grn = GoodsReceiptNoteModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            grn_number=grn_number,
            purchase_order_id=po.id,
            supplier_id=supplier_id,
            status="pending_receipt",
            driver_name=payload.get("driver_name"),
            vehicle_number=payload.get("vehicle_number"),
            transport_company=payload.get("transport_company"),
            tracking_number=payload.get("tracking_number"),
            remarks=payload.get("remarks") or "Supplier shipment notice",
            created_by=user_id,
        )
        self.session.add(grn)
        await self.session.flush()

        po_lines = {line.id: line for line in po.lines if not line.is_deleted}
        for line in payload["lines"]:
            po_line_id = line["po_line_id"]
            po_line = po_lines.get(po_line_id)
            if not po_line:
                raise ValueError(f"PO line {po_line_id} not found")
            shipped_qty = Decimal(str(line["quantity"]))
            if shipped_qty <= 0:
                raise ValueError("Shipment quantity must be positive")
            outstanding = Decimal(str(po_line.quantity)) - Decimal(str(po_line.received_quantity))
            pending = await self.session.scalar(
                select(func.coalesce(func.sum(GRNLineModel.received_quantity), 0))
                .join(GoodsReceiptNoteModel, GoodsReceiptNoteModel.id == GRNLineModel.grn_id)
                .where(
                    GoodsReceiptNoteModel.tenant_id == tenant_id,
                    GoodsReceiptNoteModel.purchase_order_id == po.id,
                    GoodsReceiptNoteModel.status == "pending_receipt",
                    GoodsReceiptNoteModel.is_deleted.is_(False),
                    GRNLineModel.po_line_id == po_line.id,
                    GRNLineModel.is_deleted.is_(False),
                )
            )
            available_to_ship = outstanding - Decimal(str(pending or 0))
            if shipped_qty > available_to_ship:
                raise ValueError(f"Shipment quantity exceeds outstanding quantity for line {po_line.id}")

            self.session.add(
                GRNLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    grn_id=grn.id,
                    po_line_id=po_line.id,
                    material_id=po_line.material_id,
                    po_quantity=po_line.quantity,
                    received_quantity=float(shipped_qty),
                    accepted_quantity=0,
                    rejected_quantity=0,
                    unit_price=po_line.unit_price,
                    remarks=line.get("remarks"),
                )
            )

        grn_id = grn.id
        await self.session.commit()
        grn = (
            await self.session.execute(
                select(GoodsReceiptNoteModel)
                .options(selectinload(GoodsReceiptNoteModel.lines))
                .where(GoodsReceiptNoteModel.id == grn_id)
            )
        ).scalar_one()
        await self._notify_procurement(
            tenant_id,
            "SUPPLIER_SHIPMENT_NOTICE",
            f"Shipment notice {grn.grn_number} submitted",
            f"Supplier submitted shipment notice for PO {po.po_number}.",
            reference_type="goods_receipt_note",
            reference_id=grn.id,
        )
        return self._grn_to_dict(grn)

    async def _counts_by_status(self, model, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> dict[str, int]:
        rows = (
            await self.session.execute(
                select(model.status, func.count(model.id))
                .where(
                    model.tenant_id == tenant_id,
                    model.supplier_id == supplier_id,
                    model.is_deleted.is_(False),
                )
                .group_by(model.status)
            )
        ).all()
        return {str(status): int(count) for status, count in rows}

    async def _recent_purchase_orders(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(PurchaseOrderModel)
                .options(selectinload(PurchaseOrderModel.lines))
                .where(
                    PurchaseOrderModel.tenant_id == tenant_id,
                    PurchaseOrderModel.supplier_id == supplier_id,
                    PurchaseOrderModel.is_deleted.is_(False),
                )
                .order_by(PurchaseOrderModel.created_at.desc())
                .limit(limit)
            )
        ).scalars().unique().all()
        return [self._po_to_dict(row) for row in rows]

    async def _supplier_or_error(self, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> SupplierModel:
        supplier = await self.session.get(SupplierModel, supplier_id)
        if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
            raise ValueError("Supplier not found")
        return supplier

    async def _purchase_order_or_error(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        po_id: uuid.UUID,
        *,
        with_lines: bool = False,
    ) -> PurchaseOrderModel:
        query = select(PurchaseOrderModel).where(
            PurchaseOrderModel.id == po_id,
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.supplier_id == supplier_id,
            PurchaseOrderModel.is_deleted.is_(False),
        )
        if with_lines:
            query = query.options(selectinload(PurchaseOrderModel.lines))
        po = (await self.session.execute(query)).scalar_one_or_none()
        if not po:
            raise ValueError("Purchase order not found")
        return po

    async def _supplier_invoice_or_error(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> SupplierInvoiceModel:
        invoice = await self.session.get(SupplierInvoiceModel, invoice_id)
        if not invoice or invoice.tenant_id != tenant_id or invoice.supplier_id != supplier_id or invoice.is_deleted:
            raise ValueError("Invoice not found")
        return invoice

    async def _notify_procurement(
        self,
        tenant_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        *,
        reference_type: Optional[str],
        reference_id: Optional[uuid.UUID],
    ) -> None:
        try:
            await NotificationService(
                self.session,
                email_service=self.email_service,
                connection_manager=self.connection_manager,
            ).broadcast_to_permission(
                tenant_id=tenant_id,
                permission="procurement:write",
                notification_type=notification_type,
                title=title,
                message=message,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        except Exception:
            # Business action already persisted; notification delivery is best effort.
            pass

    @staticmethod
    def _supplier_to_dict(supplier: SupplierModel) -> dict[str, Any]:
        required = [supplier.contact_person, supplier.email, supplier.phone, supplier.address, supplier.gst, supplier.payment_terms]
        completeness = int(sum(1 for value in required if value) / len(required) * 100)
        return {
            "id": str(supplier.id),
            "code": supplier.code,
            "name": supplier.name,
            "contact_person": supplier.contact_person,
            "email": supplier.email,
            "phone": supplier.phone,
            "address": supplier.address,
            "gst": supplier.gst,
            "payment_terms": supplier.payment_terms,
            "performance_rating": float(supplier.performance_rating) if supplier.performance_rating is not None else None,
            "is_active": supplier.is_active,
            "profile_completeness": completeness,
        }

    @staticmethod
    def _po_to_dict(po: PurchaseOrderModel) -> dict[str, Any]:
        return {
            "id": str(po.id),
            "po_number": po.po_number,
            "supplier_id": str(po.supplier_id),
            "status": po.status,
            "order_date": po.order_date.isoformat() if po.order_date else None,
            "expected_delivery": po.expected_delivery.isoformat() if po.expected_delivery else None,
            "total_amount": float(po.total_amount or 0),
            "notes": po.notes,
            "lines": [
                {
                    "id": str(line.id),
                    "material_id": str(line.material_id),
                    "quantity": float(line.quantity or 0),
                    "received_quantity": float(line.received_quantity or 0),
                    "unit_price": float(line.unit_price or 0),
                    "line_total": float(line.line_total or 0),
                }
                for line in (po.lines or [])
                if not line.is_deleted
            ],
        }

    @staticmethod
    def _quotation_to_dict(q: SupplierQuotationModel) -> dict[str, Any]:
        return {
            "id": str(q.id),
            "quotation_number": getattr(q, 'quotation_number', ''),
            "supplier_id": str(q.supplier_id),
            "purchase_order_id": str(q.purchase_order_id) if q.purchase_order_id else None,
            "material_id": str(q.material_id),
            "material_code": q.material.code if q.material else "",
            "material_name": q.material.name if q.material else "",
            "quantity": float(q.quantity or 0),
            "unit_price": float(q.unit_price or 0),
            "valid_until": q.valid_until.isoformat() if q.valid_until else None,
            "status": q.status,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "updated_at": q.updated_at.isoformat() if q.updated_at else None,
        }

    @staticmethod
    def _supplier_invoice_to_dict(invoice: SupplierInvoiceModel) -> dict[str, Any]:
        return {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "supplier_invoice_ref": invoice.supplier_invoice_ref,
            "purchase_order_id": str(invoice.purchase_order_id) if invoice.purchase_order_id else None,
            "supplier_id": str(invoice.supplier_id),
            "supplier_name": invoice.supplier_name,
            "status": invoice.status,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "subtotal": float(invoice.subtotal or 0),
            "tax_amount": float(invoice.tax_amount or 0),
            "grand_total": float(invoice.grand_total or 0),
            "paid_amount": float(invoice.paid_amount or 0),
            "balance_due": float(invoice.grand_total or 0) - float(invoice.paid_amount or 0),
            "notes": invoice.notes,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        }

    @staticmethod
    def _supplier_payment_to_dict(payment: SupplierPaymentModel) -> dict[str, Any]:
        return {
            "id": str(payment.id),
            "payment_number": payment.payment_number,
            "supplier_invoice_id": str(payment.supplier_invoice_id),
            "supplier_id": str(payment.supplier_id),
            "amount": float(payment.amount or 0),
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "payment_method": payment.payment_method,
            "reference_number": payment.reference_number,
            "notes": payment.notes,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
        }

    @staticmethod
    def _grn_to_dict(grn: GoodsReceiptNoteModel) -> dict[str, Any]:
        return {
            "id": str(grn.id),
            "grn_number": grn.grn_number,
            "purchase_order_id": str(grn.purchase_order_id),
            "supplier_id": str(grn.supplier_id),
            "status": grn.status,
            "actual_receipt_date": grn.actual_receipt_date.isoformat() if grn.actual_receipt_date else None,
            "driver_name": grn.driver_name,
            "vehicle_number": grn.vehicle_number,
            "transport_company": grn.transport_company,
            "tracking_number": grn.tracking_number,
            "remarks": grn.remarks,
            "created_at": grn.created_at.isoformat() if grn.created_at else None,
            "lines": [
                {
                    "id": str(line.id),
                    "po_line_id": str(line.po_line_id),
                    "material_id": str(line.material_id),
                    "po_quantity": float(line.po_quantity or 0),
                    "received_quantity": float(line.received_quantity or 0),
                    "accepted_quantity": float(line.accepted_quantity or 0),
                    "rejected_quantity": float(line.rejected_quantity or 0),
                    "unit_price": float(line.unit_price or 0),
                    "remarks": line.remarks,
                }
                for line in (grn.lines or [])
                if not line.is_deleted
            ],
        }
