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
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel
from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
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


async def _build_work_order_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict:
    """Build template context for Work Order PDF.
    
    Args:
        session: Async SQLAlchemy session
        tenant_id: Tenant UUID
        entity_id: Work Order UUID
        
    Returns:
        Template context dictionary
    """
    # Fetch work order with materials and job cards
    stmt = (
        select(WorkOrderModel)
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
    
    # Build materials list
    materials = []
    if wo.materials:
        for material in wo.materials:
            materials.append({
                "item_code": material.material.code if material.material else "",
                "material_name": material.material.name if material.material else material.material_id,
                "required_qty": float(material.required_quantity or 0),
                "issued_qty": float(material.issued_quantity or 0),
                "unit": material.unit.name if material.unit else "",
            })
    
    # Build operations list
    operations = []
    if wo.job_cards:
        for jc in wo.job_cards:
            operations.append({
                "sequence": jc.sequence,
                "operation_name": jc.operation.name if jc.operation else f"Operation {jc.sequence}",
                "status": jc.status,
                "work_center": jc.operation.work_center if jc.operation else "",
            })
    
    # Build template context
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": tenant.pan_number or "",
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "work_order": {
            "wo_number": wo.wo_number,
            "date": wo.created_at.strftime("%Y-%m-%d") if wo.created_at else "",
            "sales_order_number": wo.sales_order.order_number if wo.sales_order else "",
            "client": wo.client.name if wo.client else "N/A",
            "product": wo.product.name if wo.product else "N/A",
            "quantity": float(wo.planned_quantity or 0),
            "priority": wo.priority,
            "due_date": wo.due_date.strftime("%Y-%m-%d") if wo.due_date else "",
            "status": wo.status,
            "notes": wo.notes or "",
        },
        "materials": materials,
        "operations": operations,
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
    # Fetch purchase order with lines
    stmt = (
        select(PurchaseOrderModel)
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
                "item_code": line.material.code if line.material else "",
                "name": line.material.name if line.material else line.description,
                "quantity": float(line.quantity or 0),
                "unit": line.unit.name if line.unit else "",
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
            "pan_number": tenant.pan_number or "",
            "address": tenant.address or "",
            "phone": tenant.phone or "",
            "email": tenant.email or "",
            "footer_text": tenant.footer_text or "",
        },
        "purchase_order": {
            "po_number": po.po_number,
            "order_date": po.created_at.strftime("%Y-%m-%d") if po.created_at else "",
            "expected_delivery": po.expected_delivery.strftime("%Y-%m-%d") if po.expected_delivery else "",
            "supplier": po.supplier.name if po.supplier else "N/A",
            "supplier_gst": po.supplier.gst_number if po.supplier else "",
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
                "item_code": line.material.code if line.material else "",
                "name": line.material.name if line.material else line.description,
                "ordered_qty": float(line.ordered_quantity or 0),
                "unit": line.unit.name if line.unit else "",
                "delivered_qty": float(line.delivered_quantity or 0),
            })
    
    context = {
        "tenant": {
            "name": tenant.name,
            "company_name": tenant.company_name or tenant.name,
            "logo_url": tenant.logo_url or "",
            "gst_number": tenant.gst_number or "",
            "pan_number": tenant.pan_number or "",
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
            "pan_number": tenant.pan_number or "",
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
    wo_stmt = select(WorkOrderModel).where(
        WorkOrderModel.id == entity_id,
        WorkOrderModel.tenant_id == tenant_id,
        WorkOrderModel.is_deleted.is_(False),
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
    wo_stmt = select(WorkOrderModel).where(
        WorkOrderModel.id == entity_id,
        WorkOrderModel.tenant_id == tenant_id,
        WorkOrderModel.is_deleted.is_(False),
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


@router.post("/{document_type}/{entity_id}/generate", response_model=DocumentResponse)
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


@router.get("/{document_id}/download")
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
            pdf_bytes = await document_service.get_document_pdf(document_id)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=document_{document_id}.pdf"
                }
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_type}/{entity_id}/html")
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

