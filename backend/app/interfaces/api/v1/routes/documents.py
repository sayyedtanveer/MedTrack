"""Document generation API routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.application.documents.services.template_service import TemplateService
from backend.app.application.documents.services.pdf_generation_service import PDFGenerationService
from backend.app.application.documents.services.document_storage_service import DocumentStorageService
from backend.app.application.documents.services.document_generation_service import DocumentGenerationService
from backend.app.infrastructure.persistence.repositories.document_repository import DocumentRepository
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel, WorkOrderMaterialModel, JobCardModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel
from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.interfaces.api.v1.schemas.document_schemas import (
    DocumentGenerateRequest,
    DocumentResponse,
    DocumentListResponse,
    DocumentVersionResponse,
)


router = APIRouter(prefix="/documents", tags=["Documents"])


def _get_document_services(request: Request, session: AsyncSession):
    """Factory function to get document services.
    
    Args:
        request: FastAPI Request
        session: Async SQLAlchemy session
        
    Returns:
        Tuple of document services
    """
    template_service = TemplateService()
    pdf_service = PDFGenerationService()
    storage_service = DocumentStorageService()
    document_repository = DocumentRepository(session)
    document_service = DocumentGenerationService(
        template_service,
        pdf_service,
        storage_service,
        document_repository,
    )
    return document_service, storage_service


async def _build_document_control_list(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    work_order_id: uuid.UUID,
) -> list:
    """Build the Document Control list for the WO PDF.

    Returns only associations where show_on_wo=True, ordered by:
      1. WO-level docs first (no work_order_line_id), then line-specific docs
      2. Within each group, ordered by document name

    Each entry contains the fields consumed by print.html:
      name, document_category, revision, product_name (for line-specific docs)
    """
    from sqlalchemy.orm import selectinload
    from backend.app.infrastructure.persistence.models.technical_document_model import (
        DocumentAssociationModel,
        DocumentRevisionModel,
    )
    from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderLineModel

    stmt = (
        select(DocumentAssociationModel)
        .options(
            selectinload(DocumentAssociationModel.revision).selectinload(
                DocumentRevisionModel.document
            ),
        )
        .where(
            DocumentAssociationModel.tenant_id == tenant_id,
            DocumentAssociationModel.work_order_id == work_order_id,
            DocumentAssociationModel.show_on_wo.is_(True),
        )
    )
    result = await session.execute(stmt)
    associations = result.scalars().all()

    if not associations:
        return []

    # Resolve product names for line-specific associations in one pass
    line_product_names: dict[uuid.UUID, str] = {}
    line_ids = {
        assoc.work_order_line_id
        for assoc in associations
        if assoc.work_order_line_id
    }
    if line_ids:
        line_stmt = (
            select(WorkOrderLineModel.id, ItemVariantModel.name)
            .join(ItemVariantModel, ItemVariantModel.id == WorkOrderLineModel.product_id)
            .where(WorkOrderLineModel.id.in_(line_ids))
        )
        line_result = await session.execute(line_stmt)
        for line_id, product_name in line_result.all():
            line_product_names[line_id] = product_name or ""

    documents = []
    for assoc in associations:
        if not assoc.revision or not assoc.revision.document:
            continue
        doc = assoc.revision.document
        entry = {
            "name": doc.name,
            "document_category": doc.document_category,
            "revision": assoc.revision.revision_code,
            "product_name": (
                line_product_names.get(assoc.work_order_line_id, "")
                if assoc.work_order_line_id
                else ""
            ),
        }
        documents.append(entry)

    return documents


async def _build_work_order_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for Work Order PDF.
    
    Note: Materials are excluded as they're available in separate BOM download.
    This PDF focuses on operations, document control, and work instructions.
    
    Args:
        session: Async SQLAlchemy session
        tenant_id: Tenant UUID
        entity_id: Work Order UUID
        
    Returns:
        Template context dictionary
    """
    # Fetch work order with job cards only (no materials needed)
    from sqlalchemy.orm import selectinload
    stmt = (
        select(WorkOrderModel)
        .options(
            selectinload(WorkOrderModel.job_cards).selectinload(JobCardModel.operation)
        )
        .where(
            WorkOrderModel.id == entity_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
    )
    result = await session.execute(stmt)
    wo = result.scalar_one_or_none()
    
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    # Fetch tenant branding
    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()
    
    # Fetch product variant manually
    product = None
    product_code = None
    if wo.product_id:
        product_stmt = select(ItemVariantModel).where(ItemVariantModel.id == wo.product_id)
        product_result = await session.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        if product:
            product_code = product.code
        
    # Build operations list
    operations = []
    if wo.job_cards:
        for jc in wo.job_cards:
            operations.append({
                "sequence": jc.sequence,
                "operation_name": jc.operation.name if jc.operation else f"Operation {jc.sequence}",
                "status": jc.status,
                "work_center": (jc.operation.workstation.name if getattr(jc.operation, "workstation", None) else "") if jc.operation else "",
            })
    
    # Build template context (materials removed - see separate BOM download)
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": getattr(tenant, "pan_number", ""),
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "work_order": {
            "wo_number": wo.wo_number,
            "date": wo.created_at.strftime("%Y-%m-%d") if wo.created_at else "",
            "sales_order_number": getattr(wo, 'sales_order_id', ""), # Just fallback to ID if we don't have the SO loaded
            "client": getattr(wo, 'client_id', "N/A"),
            "product_code": product_code or "N/A",
            "product": product.name if product else "N/A",
            "variant": product.variant_key if product else "",
            "quantity": float(wo.planned_quantity or 0),
            "priority": wo.priority,
            "due_date": wo.due_date.strftime("%Y-%m-%d") if wo.due_date else "",
            "status": wo.status,
            "notes": wo.notes or "",
        },
        "operations": operations,
        "documents": await _build_document_control_list(session, tenant_id, entity_id),
        "signatures": {
            "planner": {
                "name": "",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "signature_image_url": tenant.signature_image_url or "",
            },
            "storekeeper": {
                "name": "",
                "timestamp": "",
                "signature_image_url": "",
            },
            "supervisor": {
                "name": "",
                "timestamp": "",
                "signature_image_url": "",
            },
            "qc": {
                "name": "",
                "timestamp": "",
                "signature_image_url": "",
            },
        },
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    
    return context


async def _build_work_order_bom_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for Work Order BOM PDF.

    Groups materials by Work Order Line when multiple product lines exist.
    For single-product WOs, emits a single flat materials list.

    Materials are drawn from the WO snapshot (work_order_materials table) —
    the data that was frozen at WO creation time, not the live BOM.

    Args:
        session: Async SQLAlchemy session
        tenant_id: Tenant UUID
        entity_id: Work Order UUID

    Returns:
        Template context dictionary
    """
    from sqlalchemy.orm import selectinload

    stmt = (
        select(WorkOrderModel)
        .options(
            selectinload(WorkOrderModel.materials).selectinload(WorkOrderMaterialModel.material),
            selectinload(WorkOrderModel.lines),
        )
        .where(
            WorkOrderModel.id == entity_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
    )
    result = await session.execute(stmt)
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()

    # Resolve single-product name for backward compat
    single_product = None
    if getattr(wo, "product_id", None):
        p_result = await session.execute(
            select(ItemVariantModel).where(ItemVariantModel.id == wo.product_id)
        )
        single_product = p_result.scalar_one_or_none()

    def _mat_dict(m: WorkOrderMaterialModel) -> dict:
        return {
            "item_code": m.material.code if m.material else "",
            "material_name": m.material.name if m.material else str(m.material_id)[:8],
            "required_qty": float(m.required_quantity or 0),
            "issued_qty": float(m.issued_quantity or 0),
            "unit": getattr(m, "unit", None).name if getattr(m, "unit", None) else "",
        }

    all_materials = [_mat_dict(m) for m in (wo.materials or [])]

    # Build per-line sections when lines exist
    product_lines: list[dict] = []
    if hasattr(wo, "lines") and wo.lines:
        # Resolve product names for each line in one pass
        line_product_names: dict[str, str] = {}
        line_bom_versions: dict[str, str] = {}
        for line in wo.lines:
            if line.product_id:
                pn_result = await session.execute(
                    select(ItemVariantModel.name).where(ItemVariantModel.id == line.product_id)
                )
                line_product_names[str(line.id)] = pn_result.scalar_one_or_none() or str(line.product_id)[:8]

        # For single-line WOs that mirror the root WO, all materials go under that line.
        # For multi-line WOs, we can only attribute materials to lines if work_order_line_id
        # is set on the material row. If not (single-product legacy path), show all under the
        # one line.
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderLineModel

        # Check if any material has work_order_line_id set
        has_line_materials = any(
            getattr(m, "work_order_line_id", None) for m in (wo.materials or [])
        )

        if has_line_materials:
            # Group materials by their line
            from collections import defaultdict
            mats_by_line: dict = defaultdict(list)
            for m in (wo.materials or []):
                line_id = str(getattr(m, "work_order_line_id", None) or "unassigned")
                mats_by_line[line_id].append(_mat_dict(m))

            for line in wo.lines:
                product_lines.append({
                    "product_name": line_product_names.get(str(line.id), f"Product {str(line.product_id)[:8]}"),
                    "planned_quantity": float(line.planned_quantity or 0),
                    "bom_version": line_bom_versions.get(str(line.id), ""),
                    "materials": mats_by_line.get(str(line.id), []),
                })
        else:
            # Single-product legacy or materials not yet split by line:
            # Show all materials under the single/first line
            if len(wo.lines) == 1:
                line = wo.lines[0]
                product_lines.append({
                    "product_name": line_product_names.get(str(line.id), "Product"),
                    "planned_quantity": float(line.planned_quantity or 0),
                    "bom_version": "",
                    "materials": all_materials,
                })
            else:
                # Multiple lines but no per-line material split — show all materials once
                # as a combined section to avoid duplication
                product_lines = []  # Fall through to single-product flat view

    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": getattr(tenant, "pan_number", ""),
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "work_order": {
            "wo_number": wo.wo_number,
            "date": wo.created_at.strftime("%Y-%m-%d") if wo.created_at else "",
            "product": single_product.name if single_product else "Multiple Products",
            "quantity": float(getattr(wo, "planned_quantity", 0) or 0),
            "priority": wo.priority,
            "due_date": wo.due_date.strftime("%Y-%m-%d") if wo.due_date else "",
            "status": wo.status,
            "notes": wo.notes or "",
        },
        # Multi-product: list of {product_name, planned_quantity, bom_version, materials[]}
        "product_lines": product_lines,
        # Single-product fallback
        "materials": all_materials,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }

    return context


async def _build_purchase_order_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for Purchase Order PDF.
    
    Args:
        session: Async SQLAlchemy session
        tenant_id: Tenant UUID
        entity_id: Purchase Order UUID
        
    Returns:
        Template context dictionary
    """
    from sqlalchemy.orm import selectinload
    stmt = (
        select(PurchaseOrderModel)
        .options(
            selectinload(PurchaseOrderModel.lines),
            selectinload(PurchaseOrderModel.supplier)
        )
        .where(
            PurchaseOrderModel.id == entity_id,
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.is_deleted.is_(False),
        )
    )
    result = await session.execute(stmt)
    po = result.scalar_one_or_none()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Fetch tenant branding
    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()
    
    # Build items list
    items = []
    if po.lines:
        for line in po.lines:
            items.append({
                "item_code": getattr(getattr(line, "material", None), "code", ""),
                "name": getattr(getattr(line, "material", None), "name", getattr(line, "description", "")),
                "quantity": float(line.quantity or 0),
                "unit": getattr(getattr(line, "unit", None), "name", ""),
                "unit_price": float(line.unit_price or 0),
                "line_total": float((line.quantity or 0) * (line.unit_price or 0)),
            })
    
    # Build template context
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": getattr(tenant, "pan_number", ""),
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "purchase_order": {
            "po_number": po.po_number,
            "order_date": po.created_at.strftime("%Y-%m-%d") if po.created_at else "",
            "expected_delivery": po.expected_delivery.strftime("%Y-%m-%d") if po.expected_delivery else "",
            "supplier": getattr(po.supplier, "name", "") if getattr(po, "supplier", None) else "N/A",
            "supplier_gst": getattr(po.supplier, "gst_number", "") if getattr(po, "supplier", None) else "",
            "status": po.status,
            "terms": po.terms or "",
            "notes": po.notes or "",
        },
        "items": items,
        "tax_breakdown": {
            "subtotal": float(po.subtotal or 0),
            "tax_amount": float(po.tax_amount or 0),
            "tax_rate": 18,  # Default GST rate
            "grand_total": float(po.grand_total or 0),
        },
        "signatures": {
            "purchasing": {
                "name": "",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "signature_image_url": tenant.signature_image_url or "",
            },
            "supplier": {
                "name": "",
                "timestamp": "",
                "signature_image_url": "",
            },
        },
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    
    return context


async def _build_invoice_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for Invoice PDF.
    
    Args:
        session: Async SQLAlchemy session
        tenant_id: Tenant UUID
        entity_id: Invoice UUID
        
    Returns:
        Template context dictionary
    """
    # Fetch invoice with lines
    stmt = (
        select(InvoiceModel)
        .options(selectinload(InvoiceModel.lines))
        .where(
            InvoiceModel.id == entity_id,
            InvoiceModel.tenant_id == tenant_id,
            InvoiceModel.is_deleted.is_(False),
        )
    )
    result = await session.execute(stmt)
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Fetch tenant branding
    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()
    
    # Build lines list
    lines = []
    if invoice.lines:
        for line in invoice.lines:
            lines.append({
                "item_code": "", # invoice_lines don't store material codes natively without a join
                "name": line.description or "Unknown Item",
                "quantity": float(line.quantity or 0),
                "unit": "Units", # Default fallback
                "unit_price": float(line.unit_price or 0),
                "line_total": float((line.quantity or 0) * (line.unit_price or 0)),
            })
    
    # Build template context
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": getattr(tenant, "pan_number", ""),
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "invoice": {
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d") if invoice.invoice_date else "",
            "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "",
            "client_name": invoice.client_name,
            "client_address": invoice.client_address or "",
            "client_gst_number": invoice.client_gst_number or "",
            "status": invoice.status,
            "terms": invoice.terms or "",
            "notes": invoice.notes or "",
        },
        "lines": lines,
        "tax_breakdown": {
            "subtotal": float(invoice.subtotal or 0),
            "discount_amount": float(invoice.discount_amount or 0),
            "tax_amount": float(invoice.tax_amount or 0),
            "grand_total": float(invoice.grand_total or 0),
            "paid_amount": float(invoice.paid_amount or 0),
            "balance_due": float(invoice.grand_total or 0) - float(invoice.paid_amount or 0),
        },
        "payment_details": {
            "bank_name": getattr(tenant, "bank_name", ""),
            "account_number": getattr(tenant, "bank_account_number", ""),
            "ifsc_code": getattr(tenant, "bank_ifsc_code", ""),
            "upi_id": getattr(tenant, "upi_id", ""),
        },
        "signatures": {
            "finance": {
                "name": "",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "signature_image_url": tenant.signature_image_url or "",
            },
            "authorized": {
                "name": "",
                "timestamp": "",
                "signature_image_url": "",
            },
        },
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    
    return context


async def _build_delivery_challan_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for Delivery Challan PDF."""
    from backend.app.infrastructure.persistence.models.deliveries_model import DeliveryModel
    
    stmt = (
        select(DeliveryModel)
        .options(selectinload(DeliveryModel.lines))
        .where(
            DeliveryModel.id == entity_id,
            DeliveryModel.tenant_id == tenant_id,
            DeliveryModel.is_deleted.is_(False),
        )
    )
    result = await session.execute(stmt)
    delivery = result.scalar_one_or_none()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()
    
    items = []
    if delivery.lines:
        for line in delivery.lines:
            items.append({
                "item_code": getattr(getattr(line, "material", None), "code", ""),
                "name": getattr(getattr(line, "material", None), "name", getattr(line, "description", "")),
                "ordered_qty": float(line.ordered_quantity or 0),
                "unit": getattr(getattr(line, "unit", None), "name", ""),
                "delivered_qty": float(line.delivered_quantity or 0),
            })
    
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": getattr(tenant, "pan_number", ""),
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "delivery_challan": {
            "challan_number": delivery.delivery_number,
            "date": delivery.delivery_date.strftime("%Y-%m-%d") if delivery.delivery_date else "",
            "customer": delivery.client.name if delivery.client else "N/A",
            "customer_address": delivery.client.address if delivery.client else "",
            "delivery_address": delivery.shipping_address or "",
            "invoice_number": delivery.invoice.invoice_number if delivery.invoice else "",
            "status": delivery.status,
            "transporter_name": delivery.transporter_name or "",
            "vehicle_number": delivery.vehicle_number or "",
            "lr_number": delivery.lr_number or "",
            "notes": delivery.notes or "",
        },
        "items": items,
        "signatures": {
            "storekeeper": {
                "name": "",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "signature_image_url": tenant.signature_image_url or "",
            },
            "transporter": {"name": "", "timestamp": "", "signature_image_url": ""},
            "receiver": {"name": "", "timestamp": "", "signature_image_url": ""},
        },
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    
    return context


async def _build_qc_report_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for QC Report PDF."""
    from backend.app.infrastructure.persistence.models.quality_model import QualityInspectionModel, InspectionDetailModel, NonConformanceReportModel
    
    stmt = select(QualityInspectionModel).where(
        QualityInspectionModel.id == entity_id,
        QualityInspectionModel.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    inspection = result.scalar_one_or_none()
    
    if not inspection:
        raise HTTPException(status_code=404, detail="Quality inspection not found")
    
    details_stmt = select(InspectionDetailModel).where(InspectionDetailModel.inspection_id == entity_id)
    details_result = await session.execute(details_stmt)
    details = details_result.scalars().all()
    
    ncr_stmt = select(NonConformanceReportModel).where(NonConformanceReportModel.inspection_id == entity_id)
    ncr_result = await session.execute(ncr_stmt)
    ncr = ncr_result.scalar_one_or_none()
    
    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()
    
    parameters = []
    for detail in details:
        parameters.append({
            "name": detail.parameter,
            "specification": "",
            "tolerance_min": float(detail.tolerance_min) if detail.tolerance_min else None,
            "tolerance_max": float(detail.tolerance_max) if detail.tolerance_max else None,
            "measured_value": detail.measured_value,
            "unit": detail.unit or "",
            "is_passed": detail.is_passed,
        })
    
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": getattr(tenant, "pan_number", ""),
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "qc_report": {
            "report_number": f"QC-{inspection.id}",
            "inspection_date": inspection.inspection_date.strftime("%Y-%m-%d") if inspection.inspection_date else "",
            "reference_type": inspection.reference_type,
            "reference_number": inspection.reference_id,
            "inspector": "",
            "result": inspection.result,
            "remarks": inspection.remarks or "",
        },
        "parameters": parameters,
        "ncr": {
            "ncr_type": ncr.ncr_type if ncr else "",
            "reason": ncr.reason if ncr else "",
            "action_taken": ncr.action_taken if ncr else "",
        } if ncr else None,
        "signatures": {
            "inspector": {
                "name": "",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "signature_image_url": tenant.signature_image_url or "",
            },
            "qc_manager": {"name": "", "timestamp": "", "signature_image_url": ""},
            "production_manager": {"name": "", "timestamp": "", "signature_image_url": ""},
        },
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    
    return context


async def _build_material_issue_slip_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for Material Issue Slip PDF."""
    from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel, WorkOrderMaterialModel
    from backend.app.infrastructure.persistence.models.material_model import MaterialModel
    
    # entity_id is the work_order_id
    wo_stmt = (
        select(WorkOrderModel)
        .options(selectinload(WorkOrderModel.product))
        .where(
            WorkOrderModel.id == entity_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
    )
    wo_result = await session.execute(wo_stmt)
    wo = wo_result.scalar_one_or_none()
    
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    mat_stmt = select(WorkOrderMaterialModel).where(
        WorkOrderMaterialModel.work_order_id == entity_id
    )
    mat_result = await session.execute(mat_stmt)
    materials = mat_result.scalars().all()
    
    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()
    
    items = []
    for material in materials:
        material_info = None
        if material.material_id:
            m_stmt = select(MaterialModel).where(MaterialModel.id == material.material_id)
            m_result = await session.execute(m_stmt)
            material_info = m_result.scalar_one_or_none()
        
        items.append({
            "item_code": material_info.code if material_info else "",
            "material_name": material_info.name if material_info else str(material.material_id),
            "required_quantity": float(material.required_quantity or 0),
            "issued_quantity": float(material.issued_quantity or 0),
            "unit": material_info.unit.name if material_info and material_info.unit else "",
        })
    
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
        },
        "issue_slip": {
            "slip_number": f"MIS-{wo.wo_number}",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "work_order_number": wo.wo_number,
            "product": wo.product.name if wo.product else "",
            "status": wo.status,
            "issued_by": "",
            "storekeeper_sign": "",
        },
        "items": items,
    }
    
    return context


async def _build_fg_receipt_note_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for FG Receipt Note PDF."""
    from backend.app.infrastructure.persistence.models.quality_model import QualityInspectionModel
    
    # entity_id is the work_order_id
    wo_stmt = (
        select(WorkOrderModel)
        .options(selectinload(WorkOrderModel.product))
        .where(
            WorkOrderModel.id == entity_id,
            WorkOrderModel.tenant_id == tenant_id,
            WorkOrderModel.is_deleted.is_(False),
        )
    )
    wo_result = await session.execute(wo_stmt)
    wo = wo_result.scalar_one_or_none()
    
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    # Get QC inspection for this WO
    qc_stmt = select(QualityInspectionModel).where(
        QualityInspectionModel.reference_id == entity_id,
        QualityInspectionModel.reference_type == "work_order",
        QualityInspectionModel.tenant_id == tenant_id,
    ).order_by(QualityInspectionModel.inspection_date.desc())
    qc_result = await session.execute(qc_stmt)
    inspection = qc_result.scalar_one_or_none()
    
    tenant_stmt = select(TenantModel).where(TenantModel.id == tenant_id)
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one()
    
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
        },
        "fg_receipt": {
            "receipt_number": f"FGR-{wo.wo_number}",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "work_order_number": wo.wo_number,
            "product_name": wo.product.name if wo.product else "",
            "product_code": wo.product.code if wo.product else "",
            "planned_quantity": float(wo.planned_quantity or 0),
            "produced_quantity": float(wo.produced_quantity or 0),
            "scrap_quantity": float(wo.scrap_quantity or 0),
            "qc_status": inspection.result if inspection else "PENDING",
            "qc_inspector": str(inspection.inspector_id) if inspection and inspection.inspector_id else "",
            "qc_date": inspection.inspection_date.strftime("%Y-%m-%d") if inspection and inspection.inspection_date else "",
            "remarks": inspection.remarks if inspection else "",
        },
        "signatures": {
            "qc_inspector": {"name": "", "timestamp": "", "signature_image_url": ""},
            "storekeeper": {"name": "", "timestamp": "", "signature_image_url": ""},
            "production_manager": {"name": "", "timestamp": "", "signature_image_url": ""},
        },
    }
    
    return context


@router.get("/test/pdf")
async def test_pdf_generation(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Test endpoint for validating PDF generation setup.
    
    Generates a simple test PDF to verify WeasyPrint is working correctly.
    """
    from backend.app.interfaces.api.v1.dependencies.auth import get_container
    container = get_container(request)
    
    # Check if PDF generation is available
    from backend.app.application.documents.services.pdf_generation_service import WEASYPRINT_AVAILABLE
    if not WEASYPRINT_AVAILABLE:
        return {
            "success": False,
            "message": "WeasyPrint is not available. Check Docker dependencies."
        }
    
    async with container.session_factory() as session:
        document_service, _ = _get_document_services(request, session)
        
        # Simple test template context
        test_context = {
            "tenant": {
                "name": "Test Tenant",
                "company_name": "Test Company",
                "logo_url": "",
                "gst_number": "",
                "address": "Test Address",
                "phone": "",
                "email": "",
                "footer_text": "Test PDF Generation",
            },
            "test_document": {
                "title": "PDF Generation Test",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "message": "WeasyPrint is working correctly!",
            },
            "items": [
                {"name": "Item 1", "value": "Test Value 1"},
                {"name": "Item 2", "value": "Test Value 2"},
                {"name": "Item 3", "value": "Test Value 3"},
            ],
        }
        
        try:
            # Generate test PDF using a simple inline template
            html_template = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; padding: 40px; }
                    h1 { color: #333; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                </style>
            </head>
            <body>
                <h1>{{ test_document.title }}</h1>
                <p><strong>Date:</strong> {{ test_document.date }}</p>
                <p>{{ test_document.message }}</p>
                <table>
                    <tr><th>Item</th><th>Value</th></tr>
                    {% for item in items %}
                    <tr><td>{{ item.name }}</td><td>{{ item.value }}</td></tr>
                    {% endfor %}
                </table>
            </body>
            </html>
            """
            
            from jinja2 import Template
            template = Template(html_template)
            html_content = template.render(**test_context)
            
            # Generate PDF
            pdf_service = document_service.pdf_service
            pdf_bytes = pdf_service.generate_pdf_from_html(html_content)
            
            # Save to storage
            storage_service = document_service.storage_service
            test_file_path = storage_service.generate_file_path(
                tenant_id=tenant_id,
                document_type="test",
                entity_id=uuid.uuid4(),
                version_number=1,
            )
            storage_service.save_pdf(pdf_bytes, test_file_path)
            
            return {
                "success": True,
                "message": "PDF generated successfully",
                "file_path": test_file_path,
                "file_size": len(pdf_bytes),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"PDF generation failed: {str(e)}",
            }


@router.post(
    "/{document_type}/{entity_id}/generate",
    response_model=DocumentResponse,
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def generate_document(
    document_type: str,
    entity_id: uuid.UUID,
    request: Request,
    body: DocumentGenerateRequest = DocumentGenerateRequest(),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Generate a document PDF for the given entity.
    
    Args:
        document_type: Type of document (work_order, purchase_order, etc.)
        entity_id: Entity UUID the document is for
        request: FastAPI Request
        body: Request body with force_regenerate flag
        tenant_id: Current tenant UUID
        user_id: Current user UUID
        
    Returns:
        Generated document metadata
    """
    from backend.app.interfaces.api.v1.dependencies.auth import get_container
    container = get_container(request)
    
    async with container.session_factory() as session:
        document_service, _ = _get_document_services(request, session)
        
        # Build template context based on document type
        if document_type == "work_order":
            template_context = await _build_work_order_context(session, tenant_id, entity_id)
        elif document_type == "work_order_bom":
            template_context = await _build_work_order_bom_context(session, tenant_id, entity_id)
        elif document_type == "purchase_order":
            template_context = await _build_purchase_order_context(session, tenant_id, entity_id)
        elif document_type == "invoice":
            template_context = await _build_invoice_context(session, tenant_id, entity_id)
        elif document_type == "delivery_challan":
            template_context = await _build_delivery_challan_context(session, tenant_id, entity_id)
        elif document_type == "qc_report":
            template_context = await _build_qc_report_context(session, tenant_id, entity_id)
        elif document_type == "material_issue_slip":
            template_context = await _build_material_issue_slip_context(session, tenant_id, entity_id)
        elif document_type == "fg_receipt_note":
            template_context = await _build_fg_receipt_note_context(session, tenant_id, entity_id)
        else:
            # TODO: Implement other document types
            template_context = {}
        
        try:
            document = await document_service.generate_document(
                tenant_id=tenant_id,
                document_type=document_type,
                entity_id=entity_id,
                template_context=template_context,
                generated_by=user_id,
                force_regenerate=body.force_regenerate,
            )
            
            # Send notification about document generation
            notification_service = container.create_notification_service(session)
            entity_number = template_context.get("work_order", {}).get("wo_number") or \
                           template_context.get("purchase_order", {}).get("po_number") or \
                           template_context.get("invoice", {}).get("invoice_number") or \
                           str(entity_id)
            await notification_service.notify_document_generated(
                tenant_id=tenant_id,
                document_id=document.id,
                document_type=document_type,
                entity_type=document_type,
                entity_id=entity_id,
                entity_number=entity_number,
                user_id=user_id,
            )
            
            await session.commit()
            return DocumentResponse.model_validate(document)
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{document_id}/download",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def download_document(
    document_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Download a document PDF.
    
    Args:
        document_id: Document UUID
        request: FastAPI Request
        tenant_id: Current tenant UUID
        
    Returns:
        PDF file as binary response
    """
    from backend.app.interfaces.api.v1.dependencies.auth import get_container
    container = get_container(request)
    
    async with container.session_factory() as session:
        document_service, _ = _get_document_services(request, session)
        
        try:
            # Verify document exists and belongs to this tenant
            doc = await document_service.document_repository.find_by_id_and_tenant(
                document_id, tenant_id
            )
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            pdf_bytes = await document_service.get_document_pdf(document_id)
            filename = f"document_{document_id}.pdf"
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{document_id}/download-package",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def download_document_package(
    document_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Download a Work Order PDF and all its technical attachments as a ZIP package."""
    from backend.app.interfaces.api.v1.dependencies.auth import get_container
    from backend.app.application.documents.services.technical_document_service import TechnicalDocumentService
    import io
    import zipfile

    container = get_container(request)

    async with container.session_factory() as session:
        document_service, _ = _get_document_services(request, session)
        from backend.app.application.documents.services.document_storage_service import DocumentStorageService
        tech_doc_service = TechnicalDocumentService(session, DocumentStorageService())

        try:
            # 1. Verify document ownership and existence
            doc = await document_service.document_repository.find_by_id_and_tenant(
                document_id, tenant_id
            )
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            # 2. Get base document PDF
            base_pdf_bytes = await document_service.get_document_pdf(document_id)

            # 3. Determine a human-readable filename stem.
            #    For work_order documents, look up the WO number.
            zip_stem = f"WO-{doc.entity_id}"
            if doc.document_type == "work_order":
                try:
                    wo_stmt = select(WorkOrderModel).where(
                        WorkOrderModel.id == doc.entity_id,
                        WorkOrderModel.tenant_id == tenant_id,
                        WorkOrderModel.is_deleted.is_(False),
                    )
                    wo_result = await session.execute(wo_stmt)
                    wo = wo_result.scalar_one_or_none()
                    if wo:
                        zip_stem = wo.wo_number
                except Exception:
                    pass  # Fall back to entity_id stem

            # 4. Build ZIP in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # ── Root: base WO PDF ────────────────────────────────────────
                zip_file.writestr(f"{zip_stem}.pdf", base_pdf_bytes)

                if doc.document_type == "work_order":
                    # ── Root: BOM PDF (generated on-the-fly) ─────────────────
                    try:
                        bom_context = await _build_work_order_bom_context(
                            session, tenant_id, doc.entity_id
                        )
                        bom_html = document_service.template_service.render_template(
                            "work_order_bom/print.html", bom_context
                        )
                        bom_pdf_bytes = document_service.pdf_service.generate_pdf_from_html(bom_html)
                        zip_file.writestr(f"{zip_stem}-BOM.pdf", bom_pdf_bytes)
                    except Exception:
                        pass  # BOM generation failure is non-fatal; skip the PDF

                    # ── Resolve product names for subfolder labels ────────────
                    # Build a map: work_order_line_id → "Product Name"
                    line_folder_names: dict[str, str] = {}
                    try:
                        from sqlalchemy.orm import selectinload as _sil
                        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderLineModel as _WOL
                        lines_stmt = (
                            select(_WOL)
                            .where(
                                _WOL.work_order_id == doc.entity_id,
                                _WOL.is_deleted.is_(False),
                            )
                        )
                        lines_result = await session.execute(lines_stmt)
                        for line in lines_result.scalars().all():
                            if line.product_id:
                                pn_result = await session.execute(
                                    select(ItemVariantModel.name).where(
                                        ItemVariantModel.id == line.product_id
                                    )
                                )
                                product_name = pn_result.scalar_one_or_none() or ""
                                # Sanitise: replace filesystem-unsafe chars
                                safe_name = (
                                    product_name
                                    .replace("/", "-")
                                    .replace("\\", "-")
                                    .replace(":", "-")
                                    .strip()
                                ) or f"Line-{str(line.id)[:8]}"
                                line_folder_names[str(line.id)] = safe_name
                    except Exception:
                        pass  # Folder naming failure is non-fatal

                    # ── Technical document attachments ────────────────────────
                    associations = await tech_doc_service.get_associations_for_entity(
                        tenant_id, "work_order", doc.entity_id
                    )
                    for assoc in associations:
                        if (
                            assoc.is_print_package_included
                            and assoc.revision
                            and assoc.revision.file_attachment
                        ):
                            try:
                                att_bytes = await tech_doc_service.get_file_content(
                                    assoc.revision.file_attachment.cloudinary_public_id
                                )
                                file_name = assoc.revision.file_attachment.file_name
                                line_id = getattr(assoc, "work_order_line_id", None)
                                if line_id:
                                    # Place in product-specific subfolder
                                    folder = line_folder_names.get(
                                        str(line_id), f"Line-{str(line_id)[:8]}"
                                    )
                                    zip_path = f"{folder}/{file_name}"
                                else:
                                    # WO-level doc: stays at root
                                    zip_path = file_name
                                zip_file.writestr(zip_path, att_bytes)
                            except Exception:
                                pass  # Skip individual failures; continue building ZIP

            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{zip_stem}.zip"'
                },
            )
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{document_type}/{entity_id}/html",
    dependencies=[Depends(require_permission("manufacturing:read"))],
)
async def get_document_html(
    document_type: str,
    entity_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get document HTML content for viewing/printing in browser.

    This endpoint is useful when PDF generation is not available (e.g., WeasyPrint missing).
    Users can view the HTML in browser and use browser's print functionality.

    Args:
        document_type: Type of document (work_order, purchase_order, etc.)
        entity_id: Entity UUID the document is for
        request: FastAPI Request
        tenant_id: Current tenant UUID

    Returns:
        HTML content as text/html response
    """
    from backend.app.interfaces.api.v1.dependencies.auth import get_container
    container = get_container(request)

    async with container.session_factory() as session:
        document_service, _ = _get_document_services(request, session)

        try:
            # Build template context based on document type
            if document_type == "work_order":
                template_context = await _build_work_order_context(session, tenant_id, entity_id)
            elif document_type == "work_order_bom":
                template_context = await _build_work_order_bom_context(session, tenant_id, entity_id)
            elif document_type == "purchase_order":
                template_context = await _build_purchase_order_context(session, tenant_id, entity_id)
            elif document_type == "invoice":
                template_context = await _build_invoice_context(session, tenant_id, entity_id)
            elif document_type == "delivery_challan":
                template_context = await _build_delivery_challan_context(session, tenant_id, entity_id)
            elif document_type == "qc_report":
                template_context = await _build_qc_report_context(session, tenant_id, entity_id)
            elif document_type == "material_issue_slip":
                template_context = await _build_material_issue_slip_context(session, tenant_id, entity_id)
            elif document_type == "fg_receipt_note":
                template_context = await _build_fg_receipt_note_context(session, tenant_id, entity_id)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown document type: {document_type}")

            # Render HTML template
            template_service = container.template_service
            template_path = template_service.get_template_path(document_type)
            html_content = template_service.render_template(template_path, template_context)

            return Response(
                content=html_content,
                media_type="text/html",
                headers={
                    "Content-Disposition": f"inline; filename=document_{document_type}_{entity_id}.html"
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_type}/{entity_id}/versions", response_model=DocumentListResponse)
async def list_document_versions(
    document_type: str,
    entity_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """List all versions of a document.
    
    Args:
        document_type: Type of document
        entity_id: Entity UUID
        request: FastAPI Request
        tenant_id: Current tenant UUID
        
    Returns:
        List of document versions
    """
    from backend.app.interfaces.api.v1.dependencies.auth import get_container
    container = get_container(request)
    
    async with container.session_factory() as session:
        document_service, _ = _get_document_services(request, session)
        
        try:
            versions = await document_service.list_document_versions(
                tenant_id=tenant_id,
                document_type=document_type,
                entity_id=entity_id,
            )
            
            version_responses = [
                DocumentVersionResponse.model_validate(v) for v in versions
            ]
            
            return DocumentListResponse(
                document_type=document_type,
                entity_id=entity_id,
                versions=version_responses,
                total=len(version_responses),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

