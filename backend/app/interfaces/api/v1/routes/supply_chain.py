from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import selectinload

from backend.app.application.manufacturing.services.inventory_service import InventoryService
from backend.app.application.manufacturing.services.workflow_orchestration_service import (
    WorkflowOrchestrationService,
)
from backend.app.application.supply_chain.po_number_service import PONumberService
from backend.app.application.supply_chain.supplier_portal_service import SupplierPortalService
from backend.app.application.supply_chain.subcontract_number_service import SubcontractNumberService
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.material_request_model import MaterialRequestModel
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderLineModel, PurchaseOrderModel
from backend.app.infrastructure.persistence.models.grn_model import (
    GoodsReceiptNoteModel,
    GRNLineModel,
)
from backend.app.infrastructure.persistence.models.quality_model import (
    InspectionDetailModel,
    NonConformanceReportModel,
    QualityInspectionModel,
    SupplierQuotationModel,
)
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.models.subcontract_model import SubcontractMaterialIssueModel, SubcontractOrderModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.application.procurement.handlers.purchase_order_handler import PurchaseOrderHandler
from backend.app.application.procurement.handlers.supplier_quotation_handler import SupplierQuotationHandler
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
    get_current_user_payload,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.dependencies.supplier_portal import require_supplier_id
from backend.app.interfaces.api.v1.schemas.supply_chain_schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse, SupplierProfileUpdate,
    SupplierShipmentNoticeLine, SupplierShipmentNoticeCreate,
    SupplierInvoiceSubmit,
    POLineIn, PurchaseOrderCreate,
    ReceiveLineItem, GoodsReceiptRequest,
    QualityInspectRequest, NCRCreateRequest,
    SubcontractOrderCreate, SubcontractIssueRequest, SubcontractReceiveRequest,
    SupplierQuotationCreate, SupplierQuotationResponse,
    MaterialRequestCreate, MaterialRequestUpdate, MaterialRequestResponse,
    RFQLineIn, RFQCreate, RFQAwardRequest,
    InvoiceDisputeCreate, InvoiceDisputeResolve,
    GRNLineCreate, GRNCreate, GRNLineResponse, GRNResponse,
)

router = APIRouter(tags=["Supply Chain"])


def _supplier_portal_service(request: Request, session) -> SupplierPortalService:
    container = get_container(request)
    return SupplierPortalService(
        session,
        email_service=getattr(container, "email_service", None),
        connection_manager=getattr(container, "connection_manager", None),
    )


async def _apply_po_receipt_to_material_requests(
    session,
    *,
    tenant_id: uuid.UUID,
    purchase_order_id: uuid.UUID,
    material_id: uuid.UUID,
    received_quantity: Decimal,
) -> None:
    """Close the shortage loop when a PO receipt fulfills an awarded RFQ's material request."""
    if received_quantity <= 0:
        return

    from backend.app.infrastructure.persistence.models.rfq_model import RFQModel

    rfq_result = await session.execute(
        select(RFQModel.material_request_id).where(
            RFQModel.tenant_id == tenant_id,
            RFQModel.awarded_po_id == purchase_order_id,
            RFQModel.material_request_id.isnot(None),
            RFQModel.is_deleted.is_(False),
        )
    )
    material_request_ids = list({mr_id for mr_id in rfq_result.scalars().all() if mr_id})
    if not material_request_ids:
        return

    mr_result = await session.execute(
        select(MaterialRequestModel)
        .where(
            MaterialRequestModel.id.in_(material_request_ids),
            MaterialRequestModel.tenant_id == tenant_id,
            MaterialRequestModel.item_type == "material",
            MaterialRequestModel.item_id == material_id,
            MaterialRequestModel.status == "open",
            MaterialRequestModel.is_deleted.is_(False),
        )
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    for material_request in mr_result.scalars().all():
        required = Decimal(str(material_request.required_quantity))
        fulfilled = Decimal(str(material_request.fulfilled_quantity or 0))
        next_fulfilled = min(required, fulfilled + received_quantity)
        material_request.fulfilled_quantity = float(next_fulfilled)
        if next_fulfilled >= required:
            material_request.status = "fulfilled"
        material_request.updated_at = now


def _po_status_text(value: str | None) -> str:
    normalized = str(value or "draft").strip().lower()
    status_aliases = {
        "partial_receipt": "partial",
        "partial-receipt": "partial",
        "partial receipt": "partial",
        "completed": "received",
        "complete": "received",
        "canceled": "cancelled",
    }
    return status_aliases.get(normalized, normalized)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _safe_iso_date(value: object) -> str | None:
    return value.isoformat() if value else None


def _po_to_dict(p: PurchaseOrderModel) -> dict:
    return {
        "id": str(p.id),
        "po_number": p.po_number,
        "supplier_id": str(p.supplier_id),
        "status": _po_status_text(p.status),
        "order_date": _safe_iso_date(p.order_date),
        "expected_delivery": _safe_iso_date(p.expected_delivery),
        "total_amount": _safe_float(p.total_amount),
        "notes": p.notes,
        "lines": [
            {
                "id": str(l.id),
                "material_id": str(l.material_id),
                "quantity": _safe_float(l.quantity),
                "received_quantity": _safe_float(l.received_quantity),
                "unit_price": _safe_float(l.unit_price),
                "line_total": _safe_float(l.line_total),
            }
            for l in p.lines
            if not l.is_deleted
        ],
    }


def _optional_uuid(value: str | uuid.UUID | None, field_name: str) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format") from e


async def _log_business_event(
    request: Request,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    summary: str,
    business_step: str,
    document_no: str | None = None,
    before_value: dict | None = None,
    after_value: dict | None = None,
    extra: dict | None = None,
) -> None:
    payload = {
        "source": "business_event",
        "module": "procurement",
        "summary": summary,
        "business_step": business_step,
        "document_no": document_no,
    }
    if extra:
        payload.update(extra)

    await get_container(request).audit_service.log_action(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_value=before_value,
        after_value=after_value,
        extra=payload,
    )


async def _first_quarantine_location(session, tenant_id: uuid.UUID) -> Optional[uuid.UUID]:
    stmt = (
        select(LocationModel.id)
        .where(
            LocationModel.tenant_id == tenant_id,
            LocationModel.type == "quarantine",
            LocationModel.is_deleted.is_(False),
            LocationModel.is_active.is_(True),
        )
        .limit(1)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def _subcontractor_location(session, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> uuid.UUID:
    """Reuse or create a location row for this supplier (type subcontractor)."""
    code = f"SUB-{supplier_id}"
    stmt = select(LocationModel).where(
        LocationModel.tenant_id == tenant_id,
        LocationModel.code == code,
        LocationModel.is_deleted.is_(False),
    )
    r = await session.execute(stmt)
    loc = r.scalar_one_or_none()
    if loc:
        return loc.id
    sup = await session.get(SupplierModel, supplier_id)
    name = f"Subcontractor: {sup.code}" if sup else f"Subcontractor {supplier_id}"
    loc = LocationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name[:100],
        type="subcontractor",
        code=code,
        is_active=True,
    )
    session.add(loc)
    await session.flush()
    return loc.id


# ── Suppliers (tenant) ────────────────────────────────────────────────────────


@router.get("/suppliers")
async def list_suppliers(
    request: Request,
    search: Optional[str] = Query(None, description="Search by code or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """List suppliers with pagination and filtering."""
    container = get_container(request)
    async with container.session_factory() as session:
        query = select(SupplierModel).where(
            SupplierModel.tenant_id == tenant_id,
            SupplierModel.is_deleted.is_(False),
        )
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (SupplierModel.code.ilike(search_term)) | (SupplierModel.name.ilike(search_term))
            )
        
        # Apply active status filter
        if is_active is not None:
            query = query.where(SupplierModel.is_active == is_active)
        
        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = await session.execute(count_stmt)
        total_count = total.scalar_one()
        
        # Paginate
        query = query.order_by(SupplierModel.code).offset(skip).limit(limit)
        r = await session.execute(query)
        rows = r.scalars().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "items": [SupplierResponse.model_validate(x) for x in rows],
    }


@router.post(
    "/suppliers",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def create_supplier(
    body: SupplierCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.inventory.services.item_code_service import ItemCodeService
        code_svc = ItemCodeService(session)

        # Handle supplier code logic
        if body.code:
            try:
                result = await code_svc.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="supplier",
                    code=body.code,
                    user_is_admin=True, # Assuming admin if they can create suppliers
                    entity_name=body.name,
                    user_id=user_id,
                )
                body.code = result.code
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            try:
                body.code = await code_svc.generate_for_entity(
                    tenant_id=tenant_id,
                    entity_type="supplier",
                    entity_name=body.name,
                    user_id=user_id,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        exists = await session.execute(
            select(SupplierModel.id).where(
                SupplierModel.tenant_id == tenant_id,
                SupplierModel.code == body.code,
                SupplierModel.is_deleted.is_(False),
            )
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Supplier code already exists")
        s = SupplierModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            code=body.code,
            name=body.name,
            contact_person=body.contact_person,
            email=body.email,
            phone=body.phone,
            address=body.address,
            gst=body.gst,
            payment_terms=body.payment_terms,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(s)
        await session.commit()
        await session.refresh(s)
    await _log_business_event(
        request,
        action="SUPPLIER_CREATED",
        entity_type="supplier",
        entity_id=s.id,
        summary=f"Supplier {s.code} created",
        business_step="Supplier master",
        document_no=s.code,
        after_value={
            "code": s.code,
            "name": s.name,
            "contact_person": s.contact_person,
            "email": s.email,
            "phone": s.phone,
            "gst": s.gst,
            "payment_terms": s.payment_terms,
        },
    )
    return SupplierResponse.model_validate(s)


@router.put(
    "/suppliers/{supplier_id}",
    response_model=SupplierResponse,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def update_supplier(
    supplier_id: uuid.UUID,
    body: SupplierUpdate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        s = await session.get(SupplierModel, supplier_id)
        if not s or s.tenant_id != tenant_id or s.is_deleted:
            raise HTTPException(status_code=404, detail="Supplier not found")
        before_value = {
            "name": s.name,
            "contact_person": s.contact_person,
            "email": s.email,
            "phone": s.phone,
            "address": s.address,
            "gst": s.gst,
            "payment_terms": s.payment_terms,
            "is_active": s.is_active,
        }
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(s, k, v)
        s.updated_by = user_id
        s.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(s)
    await _log_business_event(
        request,
        action="SUPPLIER_UPDATED",
        entity_type="supplier",
        entity_id=s.id,
        summary=f"Supplier {s.code} updated",
        business_step="Supplier master",
        document_no=s.code,
        before_value=before_value,
        after_value={
            "name": s.name,
            "contact_person": s.contact_person,
            "email": s.email,
            "phone": s.phone,
            "address": s.address,
            "gst": s.gst,
            "payment_terms": s.payment_terms,
            "is_active": s.is_active,
        },
    )
    return SupplierResponse.model_validate(s)


@router.delete(
    "/suppliers/{supplier_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_supplier(
    supplier_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Delete supplier (soft-delete). Cannot delete if supplier has active POs."""
    container = get_container(request)
    async with container.session_factory() as session:
        s = await session.get(SupplierModel, supplier_id)
        if not s or s.tenant_id != tenant_id or s.is_deleted:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Check if supplier has active (non-soft-deleted) POs
        stmt = select(PurchaseOrderModel.id).where(
            PurchaseOrderModel.supplier_id == supplier_id,
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Cannot delete supplier with active purchase orders. Archive or delete the POs first.",
            )
        
        # Soft delete the supplier
        s.is_deleted = True
        s.deleted_at = datetime.now(timezone.utc)
        await session.commit()
    return None


# ── Purchase orders ───────────────────────────────────────────────────────────


@router.get(
    "/purchase-orders",
    dependencies=[Depends(require_permission("procurement:read"))],
)
async def list_purchase_orders(
    request: Request,
    po_status: Optional[str] = Query(None, alias="status", description="Filter by status: draft, sent, acknowledged, partial, received, cancelled"),
    supplier_id: Optional[uuid.UUID] = Query(None, description="Filter by supplier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    payload: dict = Depends(get_current_user_payload),
):
    """List purchase orders with pagination and filtering.
    
    SECURITY: Supplier-role users are blocked here — they must use GET /supplier/purchase-orders instead.
    Both endpoints are properly scoped to prevent cross-supplier data leakage.
    """
    # SECURITY: Supplier-role users have procurement:read but must NOT access the tenant-wide list.
    # The /supplier/purchase-orders endpoint enforces JWT-derived supplier_id isolation.
    if payload.get("sid"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier users must use GET /supplier/purchase-orders to view their orders",
        )
    container = get_container(request)
    async with container.session_factory() as session:
        query = select(PurchaseOrderModel).where(
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.is_deleted.is_(False),
        )
        
        # Apply status filter
        if po_status:
            query = query.where(PurchaseOrderModel.status == po_status)
        
        # Apply supplier filter
        if supplier_id:
            query = query.where(PurchaseOrderModel.supplier_id == supplier_id)
        
        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = await session.execute(count_stmt)
        total_count = total.scalar_one()
        
        # Paginate
        query = query.order_by(PurchaseOrderModel.created_at.desc()).offset(skip).limit(limit)
        query = query.options(selectinload(PurchaseOrderModel.lines))
        r = await session.execute(query)
        pos = r.scalars().unique().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "items": [_po_to_dict(p) for p in pos],
    }


@router.get("/purchase-orders/{po_id}")
async def get_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == po_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        p = r.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="PO not found")
    return _po_to_dict(p)


@router.get("/purchase-orders/{po_id}/receipts")
async def get_purchase_order_receipts(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get all GRN documents for this PO."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GoodsReceiptNoteModel.purchase_order_id == po_id,
                GoodsReceiptNoteModel.is_deleted.is_(False),
            )
            .order_by(GoodsReceiptNoteModel.created_at.desc())
        )
        r = await session.execute(stmt)
        rows = r.scalars().unique().all()
        
    response = []
    for grn in rows:
        active_lines = [line for line in grn.lines if not line.is_deleted]
        line_payload = [
            {
                "id": str(line.id),
                "po_line_id": str(line.po_line_id),
                "material_id": str(line.material_id),
                "po_quantity": float(line.po_quantity or 0),
                "received_quantity": float(line.received_quantity or 0),
                "accepted_quantity": float(line.accepted_quantity or 0),
                "rejected_quantity": float(line.rejected_quantity or 0),
                "unit_price": float(line.unit_price or 0),
                "inventory_transaction_id": str(line.inventory_transaction_id) if line.inventory_transaction_id else None,
                "remarks": line.remarks,
            }
            for line in active_lines
        ]
        first_line = line_payload[0] if line_payload else None
        response.append(
            {
                "id": str(grn.id),
                "grn_number": grn.grn_number,
                "status": grn.status,
                "purchase_order_id": str(grn.purchase_order_id),
                "warehouse_location_id": str(grn.warehouse_location_id) if grn.warehouse_location_id else None,
                "actual_receipt_date": grn.actual_receipt_date.isoformat(),
                "total_received_quantity": sum(float(line.received_quantity or 0) for line in active_lines),
                "total_accepted_quantity": sum(float(line.accepted_quantity or 0) for line in active_lines),
                # Backward-compatible single-line shortcuts for simple PO receipt views.
                "material_id": first_line["material_id"] if first_line else None,
                "quantity": first_line["received_quantity"] if first_line else 0,
                "lines": line_payload,
                "remarks": grn.remarks,
                "created_at": grn.created_at.isoformat(),
            }
        )
    return response


@router.post(
    "/purchase-orders",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        if not body.lines:
            raise HTTPException(status_code=400, detail="At least one PO line is required")
        
        # CRITICAL: Validate supplier belongs to current tenant
        supplier = await session.get(SupplierModel, body.supplier_id)
        if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        po_svc = PONumberService(session)
        po_number = await po_svc.generate(tenant_id)
        total = Decimal("0")
        po = PurchaseOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            po_number=po_number,
            supplier_id=body.supplier_id,
            order_date=date.today(),
            expected_delivery=body.expected_delivery,
            status="draft",
            total_amount=0,
            notes=body.notes,
            created_by=user_id,
        )
        session.add(po)
        await session.flush()
        for line in body.lines:
            # CRITICAL: Validate material belongs to current tenant
            material = await session.get(MaterialModel, line.material_id)
            if not material or material.tenant_id != tenant_id or material.is_deleted:
                raise HTTPException(status_code=404, detail="Material not found")
            
            lt = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
            total += lt
            pl = PurchaseOrderLineModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                purchase_order_id=po.id,
                material_id=line.material_id,
                quantity=float(line.quantity),
                received_quantity=0,
                unit_price=float(line.unit_price),
                line_total=float(lt),
            )
            session.add(pl)
        po.total_amount = float(total)
        await session.commit()
    await _log_business_event(
        request,
        action="PO_CREATED",
        entity_type="purchase_order",
        entity_id=po.id,
        summary=f"Purchase order {po.po_number} created",
        business_step="Purchase order",
        document_no=po.po_number,
        after_value={
            "po_number": po.po_number,
            "supplier_id": str(po.supplier_id),
            "status": po.status,
            "total_amount": float(po.total_amount),
            "line_count": len(body.lines),
        },
    )
    return {"id": str(po.id), "po_number": po.po_number}


@router.put(
    "/purchase-orders/{po_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def update_purchase_order(
    po_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update PO (only when in draft status). Can update notes, expected_delivery, etc."""
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        if not po or po.tenant_id != tenant_id or po.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        
        # Only allow editing draft POs
        if po.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft POs can be edited")
        
        # Update allowed fields
        if "notes" in body:
            po.notes = body.get("notes")
        if "expected_delivery" in body:
            edate = body.get("expected_delivery")
            if isinstance(edate, str):
                edate = datetime.fromisoformat(edate).date()
            po.expected_delivery = edate
        
        po.updated_at = datetime.now(timezone.utc)
        po.updated_by = user_id
        await session.commit()
        await session.refresh(po, ["lines"])
    
    return _po_to_dict(po)


@router.delete(
    "/purchase-orders/{po_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Delete PO (soft-delete, only in draft status)."""
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        if not po or po.tenant_id != tenant_id or po.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        
        # Only allow deleting draft POs
        if po.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft POs can be deleted")
        
        # Soft delete the PO
        po.is_deleted = True
        await session.commit()
    return None


@router.put(
    "/purchase-orders/{po_id}/cancel",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def cancel_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Cancel PO. Can only cancel POs that haven't been fully received."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == po_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        po = r.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        
        # Cannot cancel if fully received
        if po.status == "received":
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel a fully received PO. Create a credit note or return instead.",
            )
        
        po.status = "cancelled"
        po.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "cancelled"}


@router.put(
    "/purchase-orders/{po_id}/send",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def send_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        po_number = po.po_number if po else str(po_id)
        handler = PurchaseOrderHandler(session)
        try:
            result = await handler.send_po(po_id, tenant_id)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    await _log_business_event(
        request,
        action="PO_SENT",
        entity_type="purchase_order",
        entity_id=po_id,
        summary=f"Purchase order {po_number} sent to supplier",
        business_step="Supplier collaboration",
        document_no=po_number,
        before_value={"status": "draft"},
        after_value={"status": "sent"},
    )
    return result


@router.put(
    "/purchase-orders/{po_id}/acknowledge",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def acknowledge_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        po_number = po.po_number if po else str(po_id)
        handler = PurchaseOrderHandler(session)
        try:
            result = await handler.acknowledge_po(po_id, tenant_id)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    await _log_business_event(
        request,
        action="PO_ACKNOWLEDGED",
        entity_type="purchase_order",
        entity_id=po_id,
        summary=f"Purchase order {po_number} acknowledged",
        business_step="Supplier collaboration",
        document_no=po_number,
        before_value={"status": "sent"},
        after_value={"status": "acknowledged"},
    )
    return result


# ── GRN (Goods Receipt Note) ─────────────────────────────────────────────────


@router.post(
    "/grns",
    response_model=GRNResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def create_grn(
    body: GRNCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Create a GRN (Goods Receipt Note) from a PO.
    This represents the receipt of goods from supplier and links to inventory.
    Flow: PO → GRN → Inventory Update
    """
    container = get_container(request)
    async with container.session_factory() as session:
        # Verify PO exists and belongs to tenant
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == body.purchase_order_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        po = r.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        if po.status not in ("sent", "acknowledged", "partial"):
            raise HTTPException(status_code=400, detail="PO not open for GRN")
        
        # Generate GRN number
        grn_svc = PONumberService(session)  # Reuse for GRN numbering
        grn_number = f"GRN-{await grn_svc.generate(tenant_id)}"
        
        # Create GRN header
        grn = GoodsReceiptNoteModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            grn_number=grn_number,
            purchase_order_id=body.purchase_order_id,
            supplier_id=po.supplier_id,
            warehouse_location_id=body.warehouse_location_id,
            status="pending_receipt",
            driver_name=body.driver_name,
            vehicle_number=body.vehicle_number,
            transport_company=body.transport_company,
            tracking_number=body.tracking_number,
            remarks=body.remarks,
            created_by=user_id,
        )
        session.add(grn)
        await session.flush()
        
        # Create GRN lines from PO lines
        for line in body.lines:
            # Verify line matches PO
            po_line = next(
                (ln for ln in po.lines if ln.id == line.po_line_id and not ln.is_deleted),
                None,
            )
            if not po_line:
                raise HTTPException(
                    status_code=400, detail=f"PO line {line.po_line_id} not found"
                )
            
            qty = Decimal(str(line.received_quantity))
            max_qty = Decimal(str(po_line.quantity)) - Decimal(str(po_line.received_quantity))
            if qty <= 0 or qty > max_qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid quantity for line {po_line.id}: max {max_qty}",
                )
            
            grn_line = GRNLineModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                grn_id=grn.id,
                po_line_id=po_line.id,
                material_id=po_line.material_id,
                po_quantity=po_line.quantity,
                received_quantity=float(qty),
                accepted_quantity=0,
                rejected_quantity=0,
                unit_price=po_line.unit_price,
                remarks=line.remarks,
            )
            session.add(grn_line)
        
        grn_id = grn.id
        await session.commit()
        stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(GoodsReceiptNoteModel.id == grn_id)
        )
        r = await session.execute(stmt)
        grn = r.scalar_one()
    await _log_business_event(
        request,
        action="GRN_CREATED",
        entity_type="goods_receipt_note",
        entity_id=grn.id,
        summary=f"GRN {grn.grn_number} created for PO",
        business_step="Goods receipt",
        document_no=grn.grn_number,
        after_value={
            "grn_number": grn.grn_number,
            "purchase_order_id": str(grn.purchase_order_id),
            "supplier_id": str(grn.supplier_id),
            "status": grn.status,
            "line_count": len(grn.lines),
        },
    )
    
    return GRNResponse.model_validate(grn)


@router.get("/grns/{grn_id}")
async def get_grn(
    grn_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Retrieve a specific GRN with all lines."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                GoodsReceiptNoteModel.id == grn_id,
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GoodsReceiptNoteModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        grn = r.scalar_one_or_none()
    
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")
    
    return GRNResponse.model_validate(grn)


@router.put(
    "/grns/{grn_id}/receive-in-inventory",
    response_model=dict,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def receive_grn_into_inventory(
    grn_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Mark GRN as received and update inventory with accepted quantities.
    This is the point where goods move from GRN to inventory stock.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                GoodsReceiptNoteModel.id == grn_id,
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GoodsReceiptNoteModel.is_deleted.is_(False),
            )
            .with_for_update(of=GoodsReceiptNoteModel)
        )
        r = await session.execute(stmt)
        grn = r.scalar_one_or_none()
        if not grn:
            raise HTTPException(status_code=404, detail="GRN not found")
        if grn.status != "pending_receipt":
            raise HTTPException(status_code=400, detail="GRN is not pending receipt")
        
        # Get PO with lines to update receipt totals without async lazy-loading.
        po_stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == grn.purchase_order_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        po_result = await session.execute(po_stmt)
        po = po_result.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        
        inv = InventoryService(session)
        workflow_service = WorkflowOrchestrationService(session)
        
        # For each GRN line, update inventory and PO line
        for grn_line in grn.lines:
            if grn_line.is_deleted:
                continue
            
            # Set accepted quantity to received quantity (full acceptance)
            accepted_qty = Decimal(str(grn_line.received_quantity))
            grn_line.accepted_quantity = float(accepted_qty)
            
            # Find the PO line and update its received_quantity
            po_line = await session.get(PurchaseOrderLineModel, grn_line.po_line_id)
            if po_line:
                po_line.received_quantity = float(
                    Decimal(str(po_line.received_quantity)) + accepted_qty
                )
            
            # Get material details for unit
            material = await session.get(MaterialModel, grn_line.material_id)
            
            # Log inventory receipt (CRITICAL: reference GRN, not purchase_receipt)
            await inv.receive_purchase_receipt(
                tenant_id=tenant_id,
                material_id=grn_line.material_id,
                quantity=accepted_qty,
                purchase_order_id=po.id,
                unit_id=material.base_unit_id if material else None,
                created_by=user_id,
                warehouse_location_id=grn.warehouse_location_id,
                unit_cost=grn_line.unit_price,
            )
            await workflow_service.on_goods_received(
                tenant_id=tenant_id,
                purchase_order_id=po.id,
                material_id=grn_line.material_id,
                quantity=accepted_qty,
            )
            await _apply_po_receipt_to_material_requests(
                session,
                tenant_id=tenant_id,
                purchase_order_id=po.id,
                material_id=grn_line.material_id,
                received_quantity=accepted_qty,
            )
            
            # Record supplier price history
            await session.execute(
                text("""
                    INSERT INTO supplier_price_history (
                        id, tenant_id, supplier_id, material_id, unit_price, effective_from, created_at
                    ) VALUES (
                        :id, :tid, :sid, :mid, :up, :effective_from, :created_at
                    )
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tid": str(tenant_id),
                    "sid": str(po.supplier_id),
                    "mid": str(grn_line.material_id),
                    "up": float(grn_line.unit_price),
                    "effective_from": date.today(),
                    "created_at": datetime.now(timezone.utc),
                },
            )
        
        # Update GRN status to received
        grn.status = "received"
        grn.updated_by = user_id
        grn.updated_at = datetime.now(timezone.utc)
        
        # Update PO status based on completion
        all_done = all(
            Decimal(str(l.received_quantity)) >= Decimal(str(l.quantity))
            for l in po.lines
            if not l.is_deleted
        )
        any_recv = any(Decimal(str(l.received_quantity)) > 0 for l in po.lines if not l.is_deleted)
        if all_done:
            po.status = "received"
        elif any_recv:
            po.status = "partial"
        po.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
        grn_number = grn.grn_number
        po_number = po.po_number
    
    await _log_business_event(
        request,
        action="GRN_RECEIVED",
        entity_type="goods_receipt_note",
        entity_id=grn_id,
        summary=f"GRN {grn_number} received into inventory",
        business_step="Inventory receipt",
        document_no=grn_number,
        before_value={"status": "pending_receipt"},
        after_value={"status": "received", "purchase_order_status": po.status},
        extra={"purchase_order_id": str(po.id), "purchase_order_no": po_number},
    )
    return {"grn_id": str(grn.id), "status": grn.status, "po_id": str(po.id)}


@router.put(
    "/purchase-orders/{po_id}/receive",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def receive_goods(
    po_id: uuid.UUID,
    body: GoodsReceiptRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == po_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
            .with_for_update(of=PurchaseOrderModel)
        )
        r = await session.execute(stmt)
        po = r.scalar_one_or_none()
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")
        if po.status not in ("sent", "acknowledged", "partial"):
            raise HTTPException(status_code=400, detail="PO not open for receiving")

        inv = InventoryService(session)
        grn_number = f"GRN-{await PONumberService(session).generate(tenant_id)}"
        grn = GoodsReceiptNoteModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            grn_number=grn_number,
            purchase_order_id=po.id,
            supplier_id=po.supplier_id,
            warehouse_location_id=body.warehouse_location_id,
            status="received",
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(grn)
        await session.flush()

        for item in body.lines:
            lid = next((ln for ln in po.lines if ln.id == item.line_id and not ln.is_deleted), None)
            if not lid:
                raise HTTPException(status_code=400, detail=f"Line {item.line_id} not on PO")
            qty = Decimal(str(item.quantity))
            max_recv = Decimal(str(lid.quantity)) - Decimal(str(lid.received_quantity))
            if qty <= 0 or qty > max_recv:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid receive qty for line {lid.id}: max {max_recv}",
                )
            mat = await session.get(MaterialModel, lid.material_id)
            await inv.receive_purchase_receipt(
                tenant_id=tenant_id,
                material_id=lid.material_id,
                quantity=qty,
                purchase_order_id=po.id,
                unit_id=mat.base_unit_id if mat else None,
                created_by=user_id,
                warehouse_location_id=body.warehouse_location_id,
            )
            lid.received_quantity = float(Decimal(str(lid.received_quantity)) + qty)
            session.add(
                GRNLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    grn_id=grn.id,
                    po_line_id=lid.id,
                    material_id=lid.material_id,
                    po_quantity=lid.quantity,
                    received_quantity=float(qty),
                    accepted_quantity=float(qty),
                    rejected_quantity=0,
                    unit_price=lid.unit_price,
                )
            )
            await _apply_po_receipt_to_material_requests(
                session,
                tenant_id=tenant_id,
                purchase_order_id=po.id,
                material_id=lid.material_id,
                received_quantity=qty,
            )
            await session.execute(
                text("""
                    INSERT INTO supplier_price_history (
                        id, tenant_id, supplier_id, material_id, unit_price, effective_from, created_at
                    ) VALUES (
                        :id, :tid, :sid, :mid, :up, :effective_from, :created_at
                    )
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tid": str(tenant_id),
                    "sid": str(po.supplier_id),
                    "mid": str(lid.material_id),
                    "up": float(lid.unit_price),
                    "effective_from": date.today(),
                    "created_at": datetime.now(timezone.utc),
                },
            )

        # PO status
        all_done = all(
            Decimal(str(l.received_quantity)) >= Decimal(str(l.quantity))
            for l in po.lines
            if not l.is_deleted
        )
        any_recv = any(Decimal(str(l.received_quantity)) > 0 for l in po.lines if not l.is_deleted)
        if all_done:
            po.status = "received"
        elif any_recv:
            po.status = "partial"
        po.updated_at = datetime.now(timezone.utc)
        grn.updated_at = datetime.now(timezone.utc)
        await session.commit()
        po_number = po.po_number
        po_status = po.status
        grn_id = grn.id
    await _log_business_event(
        request,
        action="PO_RECEIVED",
        entity_type="purchase_order",
        entity_id=po_id,
        summary=f"Goods received against PO {po_number}",
        business_step="Inventory receipt",
        document_no=po_number,
        after_value={
            "status": po_status,
            "line_count": len(body.lines),
        },
    )
    return {"status": "ok", "grn_id": str(grn_id)}


@router.put(
    "/purchase-orders/{po_id}/lines/{line_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def update_po_line(
    po_id: uuid.UUID,
    line_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update PO line (only when PO is in draft status)."""
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        if not po or po.tenant_id != tenant_id or po.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        
        # Only allow editing draft POs
        if po.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft POs can be edited")
        
        # Find the line
        line = None
        for lin in po.lines:
            if lin.id == line_id and not lin.is_deleted:
                line = lin
                break
        
        if not line:
            raise HTTPException(status_code=404, detail="Line not found")
        
        # Update allowed fields
        if "quantity" in body:
            new_qty = float(body.get("quantity"))
            if new_qty <= 0:
                raise HTTPException(status_code=400, detail="Quantity must be > 0")
            line.quantity = new_qty
        
        if "unit_price" in body:
            new_price = float(body.get("unit_price"))
            if new_price < 0:
                raise HTTPException(status_code=400, detail="Unit price cannot be negative")
            line.unit_price = new_price
        
        # Recalculate line total
        line.line_total = float(Decimal(str(line.quantity)) * Decimal(str(line.unit_price)))
        
        # Recalculate PO total
        total = Decimal("0")
        for lin in po.lines:
            if not lin.is_deleted:
                total += Decimal(str(lin.line_total or 0))
        po.total_amount = float(total)
        po.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
    
    return {
        "id": str(line.id),
        "material_id": str(line.material_id),
        "quantity": line.quantity,
        "unit_price": line.unit_price,
        "line_total": line.line_total,
    }


@router.delete(
    "/purchase-orders/{po_id}/lines/{line_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_po_line(
    po_id: uuid.UUID,
    line_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Delete PO line (soft-delete, only when PO is in draft status)."""
    container = get_container(request)
    async with container.session_factory() as session:
        po = await session.get(PurchaseOrderModel, po_id)
        if not po or po.tenant_id != tenant_id or po.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        
        # Only allow editing draft POs
        if po.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft POs can be edited")
        
        # Find the line
        line = None
        for lin in po.lines:
            if lin.id == line_id and not lin.is_deleted:
                line = lin
                break
        
        if not line:
            raise HTTPException(status_code=404, detail="Line not found")
        
        # Soft delete the line
        line.is_deleted = True
        
        # Recalculate PO total (excluding deleted lines)
        total = Decimal("0")
        for lin in po.lines:
            if not lin.is_deleted:
                total += Decimal(str(lin.line_total or 0))
        po.total_amount = float(total)
        po.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
    return None


# ── Material Requests ─────────────────────────────────────────────────────────


@router.get("/material-requests")
async def list_material_requests(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: open, fulfilled, cancelled"),
    item_type: Optional[str] = Query(None, description="Filter by item_type: material, component, product"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """List material requests with pagination and filtering."""
    container = get_container(request)
    async with container.session_factory() as session:
        query = select(MaterialRequestModel).where(
            MaterialRequestModel.tenant_id == tenant_id,
            MaterialRequestModel.is_deleted.is_(False),
        )
        if status:
            query = query.where(MaterialRequestModel.status == status)
        if item_type:
            query = query.where(MaterialRequestModel.item_type == item_type)
        
        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = await session.execute(count_stmt)
        total_count = total.scalar_one()
        
        # Paginate
        query = query.order_by(MaterialRequestModel.created_at.desc()).offset(skip).limit(limit)
        r = await session.execute(query)
        reqs = r.scalars().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "items": [MaterialRequestResponse.model_validate(x) for x in reqs],
    }


@router.get("/material-requests/{mr_id}", response_model=MaterialRequestResponse)
async def get_material_request(
    mr_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get a specific material request."""
    container = get_container(request)
    async with container.session_factory() as session:
        mr = await session.get(MaterialRequestModel, mr_id)
        if not mr or mr.tenant_id != tenant_id or mr.is_deleted:
            raise HTTPException(status_code=404, detail="Material request not found")
    return MaterialRequestResponse.model_validate(mr)


@router.post(
    "/material-requests",
    response_model=MaterialRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def create_material_request(
    body: MaterialRequestCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create a new material request."""
    container = get_container(request)
    async with container.session_factory() as session:
        # Validate the item exists in the current tenant
        if body.item_type == "material":
            item = await session.get(MaterialModel, body.item_id)
            if not item or item.tenant_id != tenant_id or item.is_deleted:
                raise HTTPException(status_code=404, detail="Material not found")
        # Can extend to validate other item_types (component, product) as needed
        
        mr = MaterialRequestModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            item_id=body.item_id,
            item_type=body.item_type,
            required_quantity=float(body.required_quantity),
            required_by=body.required_by,
            status="open",
            source_ref_type=body.source_ref_type,
            source_ref_id=body.source_ref_id,
        )
        session.add(mr)
        await session.commit()
        await session.refresh(mr)
    return MaterialRequestResponse.model_validate(mr)


@router.put(
    "/material-requests/{mr_id}",
    response_model=MaterialRequestResponse,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def update_material_request(
    mr_id: uuid.UUID,
    body: MaterialRequestUpdate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update a material request (only if status is open)."""
    container = get_container(request)
    async with container.session_factory() as session:
        mr = await session.get(MaterialRequestModel, mr_id)
        if not mr or mr.tenant_id != tenant_id or mr.is_deleted:
            raise HTTPException(status_code=404, detail="Material request not found")
        
        if mr.status != "open":
            raise HTTPException(status_code=400, detail="Can only update open material requests")
        
        if body.required_quantity is not None:
            mr.required_quantity = float(body.required_quantity)
        if body.required_by is not None:
            mr.required_by = body.required_by
        
        await session.commit()
        await session.refresh(mr)
    return MaterialRequestResponse.model_validate(mr)


@router.delete(
    "/material-requests/{mr_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_material_request(
    mr_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Delete material request (soft-delete, only if status is open)."""
    container = get_container(request)
    async with container.session_factory() as session:
        mr = await session.get(MaterialRequestModel, mr_id)
        if not mr or mr.tenant_id != tenant_id or mr.is_deleted:
            raise HTTPException(status_code=404, detail="Material request not found")
        
        if mr.status != "open":
            raise HTTPException(status_code=400, detail="Can only delete open material requests")
        
        mr.is_deleted = True
        mr.deleted_at = datetime.now(timezone.utc)
        await session.commit()
    return None


# ── GRN (Goods Receipt Notes) ─────────────────────────────────────────────────


@router.get("/grn", deprecated=True, dependencies=[Depends(require_permission("procurement:read"))])
async def list_grns(
    request: Request,
    purchase_order_id: Optional[uuid.UUID] = Query(None, description="Filter by PO"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Deprecated legacy GRN list. Mirrors GRN documents from /grns."""
    container = get_container(request)
    async with container.session_factory() as session:
        query = select(GoodsReceiptNoteModel).where(
            GoodsReceiptNoteModel.tenant_id == tenant_id,
            GoodsReceiptNoteModel.is_deleted.is_(False),
        )
        if purchase_order_id:
            query = query.where(GoodsReceiptNoteModel.purchase_order_id == purchase_order_id)
        
        # Total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total = await session.execute(count_stmt)
        total_count = total.scalar_one()
        
        # Paginated results
        query = (
            query
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .order_by(GoodsReceiptNoteModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        r = await session.execute(query)
        grns = r.scalars().unique().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(grn.id),
                "grn_number": grn.grn_number,
                "purchase_order_id": str(grn.purchase_order_id),
                "supplier_id": str(grn.supplier_id),
                "status": grn.status,
                "warehouse_location_id": str(grn.warehouse_location_id) if grn.warehouse_location_id else None,
                "total_received_quantity": sum(float(line.received_quantity or 0) for line in grn.lines if not line.is_deleted),
                "remarks": grn.remarks,
                "created_by": str(grn.created_by),
                "created_at": grn.created_at.isoformat(),
            }
            for grn in grns
        ],
    }


@router.get("/grn/{grn_id}", deprecated=True, dependencies=[Depends(require_permission("procurement:read"))])
async def get_grn(
    grn_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Deprecated legacy GRN detail. Mirrors a GRN document from /grns/{id}."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                GoodsReceiptNoteModel.id == grn_id,
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GoodsReceiptNoteModel.is_deleted.is_(False),
            )
        )
        t = (await session.execute(stmt)).scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="GRN not found")
    
    return {
        "id": str(t.id),
        "grn_number": t.grn_number,
        "purchase_order_id": str(t.purchase_order_id),
        "supplier_id": str(t.supplier_id),
        "warehouse_location_id": str(t.warehouse_location_id) if t.warehouse_location_id else None,
        "status": t.status,
        "remarks": t.remarks,
        "created_by": str(t.created_by),
        "created_at": t.created_at.isoformat(),
        "lines": [
            {
                "id": str(line.id),
                "po_line_id": str(line.po_line_id),
                "material_id": str(line.material_id),
                "po_quantity": float(line.po_quantity),
                "received_quantity": float(line.received_quantity),
                "accepted_quantity": float(line.accepted_quantity or 0),
                "rejected_quantity": float(line.rejected_quantity or 0),
                "unit_price": float(line.unit_price),
                "inventory_transaction_id": str(line.inventory_transaction_id) if line.inventory_transaction_id else None,
                "remarks": line.remarks,
            }
            for line in t.lines
            if not line.is_deleted
        ],
    }


@router.post("/grn/{grn_id}/reverse", deprecated=True, dependencies=[Depends(require_permission("procurement:write"))])
async def reverse_grn(
    grn_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Reverse a legacy GRN endpoint using the canonical inventory service."""
    container = get_container(request)
    async with container.session_factory() as session:
        document_stmt = (
            select(GoodsReceiptNoteModel)
            .options(selectinload(GoodsReceiptNoteModel.lines))
            .where(
                GoodsReceiptNoteModel.id == grn_id,
                GoodsReceiptNoteModel.tenant_id == tenant_id,
                GoodsReceiptNoteModel.is_deleted.is_(False),
            )
            .with_for_update(of=GoodsReceiptNoteModel)
        )
        grn = (await session.execute(document_stmt)).scalar_one_or_none()

        if grn is not None:
            if grn.status != "received":
                raise HTTPException(status_code=400, detail="Only received GRNs can be reversed")

            inv = InventoryService(session)
            reversed_lines = 0
            po_stmt = (
                select(PurchaseOrderModel)
                .options(selectinload(PurchaseOrderModel.lines))
                .where(
                    PurchaseOrderModel.id == grn.purchase_order_id,
                    PurchaseOrderModel.tenant_id == tenant_id,
                    PurchaseOrderModel.is_deleted.is_(False),
                )
                .with_for_update(of=PurchaseOrderModel)
            )
            po = (await session.execute(po_stmt)).scalar_one_or_none()

            for line in grn.lines:
                if line.is_deleted:
                    continue
                reverse_qty = Decimal(str(line.accepted_quantity or line.received_quantity or 0))
                if reverse_qty <= 0:
                    continue

                material = await session.get(MaterialModel, line.material_id)
                await inv.reverse_purchase_receipt(
                    tenant_id=tenant_id,
                    material_id=line.material_id,
                    quantity=reverse_qty,
                    purchase_order_id=grn.purchase_order_id,
                    unit_id=material.base_unit_id if material else None,
                    created_by=user_id,
                    warehouse_location_id=grn.warehouse_location_id,
                    reference_type="grn_reversal",
                    reference_id=grn.id,
                    remarks=f"Reversal of GRN {grn.grn_number}",
                )

                po_line = await session.get(PurchaseOrderLineModel, line.po_line_id)
                if po_line is not None:
                    po_line.received_quantity = float(
                        max(Decimal("0"), Decimal(str(po_line.received_quantity or 0)) - reverse_qty)
                    )
                line.accepted_quantity = 0
                line.inventory_transaction_id = None
                reversed_lines += 1

            grn.status = "reversed"
            grn.updated_by = user_id
            grn.updated_at = datetime.now(timezone.utc)

            if po is not None:
                active_lines = [po_line for po_line in po.lines if not po_line.is_deleted]
                all_done = bool(active_lines) and all(
                    Decimal(str(po_line.received_quantity or 0)) >= Decimal(str(po_line.quantity or 0))
                    for po_line in active_lines
                )
                any_recv = any(Decimal(str(po_line.received_quantity or 0)) > 0 for po_line in active_lines)
                if all_done:
                    po.status = "received"
                elif any_recv:
                    po.status = "partial"
                else:
                    po.status = "acknowledged" if po.status in {"acknowledged", "partial", "received"} else "sent"
                po.updated_at = datetime.now(timezone.utc)

            await session.commit()
            return {
                "status": "reversed",
                "original_grn_id": str(grn_id),
                "reversed_lines": reversed_lines,
            }

        original_grn = await session.get(InventoryTransactionModel, grn_id)
        if not original_grn or original_grn.tenant_id != tenant_id or original_grn.is_deleted:
            raise HTTPException(status_code=404, detail="GRN not found")
        if original_grn.reference_type != "purchase_receipt":
            raise HTTPException(status_code=400, detail="Can only reverse purchase receipts")

        inv = InventoryService(session)
        await inv.reverse_purchase_receipt(
            tenant_id=tenant_id,
            material_id=original_grn.material_id,
            quantity=Decimal(str(original_grn.quantity or 0)),
            purchase_order_id=original_grn.reference_id,
            unit_id=original_grn.unit_id,
            created_by=user_id,
            warehouse_location_id=original_grn.to_location_id,
            reference_type="purchase_receipt_reversal",
            reference_id=original_grn.id,
            remarks=f"Reversal of legacy GRN {grn_id}",
        )
        original_grn.is_deleted = True
        original_grn.deleted_at = datetime.now(timezone.utc)
        await session.commit()

    return {
        "status": "reversed",
        "original_grn_id": str(grn_id),
    }


# ── Quality ───────────────────────────────────────────────────────────────────


@router.post("/quality/inspect", dependencies=[Depends(require_permission("quality:write"))])
async def quality_inspect(
    body: QualityInspectRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        qi = QualityInspectionModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
            inspection_date=date.today(),
            inspector_id=user_id,
            result=body.result,
            remarks=body.remarks,
        )
        session.add(qi)
        await session.flush()
        if body.details:
            for d in body.details:
                session.add(
                    InspectionDetailModel(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        inspection_id=qi.id,
                        parameter=str(d.get("parameter", "")),
                        measured_value=d.get("measured_value"),
                        tolerance_min=d.get("tolerance_min"),
                        tolerance_max=d.get("tolerance_max"),
                        is_passed=bool(d.get("is_passed", False)),
                    )
                )
        inv = InventoryService(session)
        if body.result == "pass":
            await inv.inspection_pass_move_to_available(
                tenant_id=tenant_id,
                material_id=body.material_id,
                quantity=body.quantity,
                warehouse_location_id=body.warehouse_location_id,
                inspection_id=qi.id,
                created_by=user_id,
            )
        elif body.result in ("fail", "rework"):
            q_loc = await _first_quarantine_location(session, tenant_id)
            if not q_loc:
                raise HTTPException(
                    status_code=400,
                    detail="No quarantine location (type=quarantine). Create one under Locations.",
                )
            await inv.inspection_fail_move_to_quarantine(
                tenant_id=tenant_id,
                material_id=body.material_id,
                quantity=body.quantity,
                warehouse_location_id=body.warehouse_location_id,
                quarantine_location_id=q_loc,
                inspection_id=qi.id,
                created_by=user_id,
            )
        await session.commit()
    return {"inspection_id": str(qi.id)}


@router.post("/quality/ncr", dependencies=[Depends(require_permission("quality:write"))])
async def create_ncr(
    body: NCRCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        ncr = NonConformanceReportModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            inspection_id=body.inspection_id,
            ncr_type=body.ncr_type,
            reason=body.reason,
            action_taken=body.action_taken,
        )
        session.add(ncr)
        await session.commit()
    return {"id": str(ncr.id)}


@router.get("/quality/ncrs")
async def list_ncrs(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(NonConformanceReportModel).where(NonConformanceReportModel.tenant_id == tenant_id)
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [
        {
            "id": str(x.id),
            "inspection_id": str(x.inspection_id) if x.inspection_id else None,
            "ncr_type": x.ncr_type,
            "reason": x.reason,
            "action_taken": x.action_taken,
            "created_at": x.created_at.isoformat() if x.created_at else None,
        }
        for x in rows
    ]


@router.get("/quarantine-stock")
async def quarantine_stock(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Quantities in quarantine status by material and location."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(
                StockLevelModel.material_id,
                StockLevelModel.location_id,
                StockLevelModel.quantity,
                MaterialModel.code,
                MaterialModel.name,
                LocationModel.name,
            )
            .join(MaterialModel, MaterialModel.id == StockLevelModel.material_id)
            .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.stock_status == "quarantine",
                StockLevelModel.is_deleted.is_(False),
                StockLevelModel.quantity > 0,
            )
        )
        r = await session.execute(stmt)
        rows = r.all()
    return [
        {
            "material_id": str(m_id),
            "material_code": code,
            "material_name": name,
            "location_id": str(loc_id),
            "location_name": loc_name,
            "quantity": float(qty),
        }
        for m_id, loc_id, qty, code, name, loc_name in rows
    ]


# ── Subcontract ───────────────────────────────────────────────────────────────


@router.post(
    "/subcontract/orders",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def create_subcontract_order(
    body: SubcontractOrderCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        num = SubcontractNumberService(session)
        on = await num.generate(tenant_id)
        o = SubcontractOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            order_number=on,
            supplier_id=body.supplier_id,
            product_id=body.product_id,
            product_type=body.product_type,
            quantity=float(body.quantity),
            status="draft",
        )
        session.add(o)
        await session.commit()
    return {"id": str(o.id), "order_number": on}


@router.get("/subcontract/orders")
async def list_subcontract_orders(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: draft, issued, received"),
    supplier_id: Optional[uuid.UUID] = Query(None, description="Filter by supplier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """List subcontract orders with pagination and filtering."""
    container = get_container(request)
    async with container.session_factory() as session:
        query = select(SubcontractOrderModel).where(
            SubcontractOrderModel.tenant_id == tenant_id,
            SubcontractOrderModel.is_deleted.is_(False),
        )
        
        if status:
            query = query.where(SubcontractOrderModel.status == status)
        if supplier_id:
            query = query.where(SubcontractOrderModel.supplier_id == supplier_id)
        
        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = await session.execute(count_stmt)
        total_count = total.scalar_one()
        
        # Paginate
        query = query.order_by(SubcontractOrderModel.created_at.desc()).offset(skip).limit(limit)
        r = await session.execute(query)
        rows = r.scalars().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(x.id),
                "order_number": x.order_number,
                "supplier_id": str(x.supplier_id),
                "product_id": str(x.product_id),
                "product_type": x.product_type,
                "quantity": float(x.quantity),
                "status": x.status,
            }
            for x in rows
        ],
    }


@router.get("/subcontract/orders/{order_id}")
async def get_subcontract_order(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        o = await session.get(SubcontractOrderModel, order_id)
        if not o or o.tenant_id != tenant_id or o.is_deleted:
            raise HTTPException(status_code=404, detail="Subcontract order not found")
        iss_stmt = select(SubcontractMaterialIssueModel).where(
            SubcontractMaterialIssueModel.subcontract_order_id == order_id,
            SubcontractMaterialIssueModel.tenant_id == tenant_id,
        )
        ir = await session.execute(iss_stmt)
        issues = ir.scalars().all()
    return {
        "id": str(o.id),
        "order_number": o.order_number,
        "supplier_id": str(o.supplier_id),
        "product_id": str(o.product_id),
        "product_type": o.product_type,
        "quantity": float(o.quantity),
        "status": o.status,
        "issues": [
            {
                "id": str(i.id),
                "material_id": str(i.material_id),
                "quantity": float(i.quantity),
                "batch_number": i.batch_number,
                "issued_at": i.issued_at.isoformat() if i.issued_at else None,
            }
            for i in issues
        ],
    }


@router.post(
    "/subcontract/orders/{order_id}/issue",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def issue_subcontract_material(
    order_id: uuid.UUID,
    body: SubcontractIssueRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        o = await session.get(SubcontractOrderModel, order_id)
        if not o or o.tenant_id != tenant_id or o.is_deleted:
            raise HTTPException(status_code=404, detail="Subcontract order not found")
        sub_loc = await _subcontractor_location(session, tenant_id, o.supplier_id)
        mat = await session.get(MaterialModel, body.material_id)
        inv = InventoryService(session)
        await inv.issue_to_subcontractor(
            tenant_id=tenant_id,
            material_id=body.material_id,
            quantity=body.quantity,
            from_location_id=body.from_location_id,
            subcontractor_location_id=sub_loc,
            subcontract_order_id=o.id,
            unit_id=mat.base_unit_id if mat else None,
            created_by=user_id,
        )
        session.add(
            SubcontractMaterialIssueModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                subcontract_order_id=o.id,
                material_id=body.material_id,
                quantity=float(body.quantity),
                batch_number=body.batch_number,
            )
        )
        o.status = "issued"
        o.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


@router.post(
    "/subcontract/orders/{order_id}/receive",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def receive_subcontract(
    order_id: uuid.UUID,
    body: SubcontractReceiveRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        o = await session.get(SubcontractOrderModel, order_id)
        if not o or o.tenant_id != tenant_id or o.is_deleted:
            raise HTTPException(status_code=404, detail="Subcontract order not found")
        mat = await session.get(MaterialModel, body.material_id)
        inv = InventoryService(session)
        await inv.receive_subcontract_finished_goods(
            tenant_id=tenant_id,
            material_id=body.material_id,
            quantity=body.quantity,
            warehouse_location_id=body.warehouse_location_id,
            subcontract_order_id=o.id,
            unit_id=mat.base_unit_id if mat else None,
            created_by=user_id,
        )
        o.status = "received"
        o.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "ok"}


# ── Material Requests (continued) ────────────────────────────────────────────


@router.post(
    "/material-requests/run-mrp",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def run_mrp(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Generate open material_requests where available + incoming - reserved < reorder + safety."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
            MaterialModel.material_type == "raw",
        )
        r = await session.execute(stmt)
        materials = r.scalars().all()
        inv = InventoryService(session)
        created = 0
        for m in materials:
            rl = m.reorder_level
            if rl is None:
                continue
            rl_d = Decimal(str(rl))
            safety = Decimal(str(m.safety_stock)) if m.safety_stock is not None else Decimal("0")
            avail = await inv._sum_available_internal(tenant_id, m.id)  # noqa: SLF001
            if not await inv._has_stock_levels(tenant_id, m.id):  # noqa: SLF001
                avail = Decimal(str(m.current_stock)) - Decimal(str(m.reserved_stock))
            reserved = Decimal(str(m.reserved_stock))
            q_in = await session.execute(
                select(
                    func.coalesce(
                        func.sum(
                            PurchaseOrderLineModel.quantity - PurchaseOrderLineModel.received_quantity
                        ),
                        0,
                    )
                )
                .join(PurchaseOrderModel, PurchaseOrderModel.id == PurchaseOrderLineModel.purchase_order_id)
                .where(
                    PurchaseOrderLineModel.tenant_id == tenant_id,
                    PurchaseOrderLineModel.material_id == m.id,
                    PurchaseOrderLineModel.is_deleted.is_(False),
                    PurchaseOrderModel.is_deleted.is_(False),
                    PurchaseOrderModel.status.in_(("sent", "acknowledged", "partial")),
                )
            )
            incoming = Decimal(str(q_in.scalar_one()))
            net = avail + incoming - reserved
            need = rl_d + safety - net
            if need > 0:
                mr = MaterialRequestModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    item_id=m.id,
                    item_type="material",
                    required_quantity=float(need),
                    fulfilled_quantity=0,
                    status="open",
                    source_ref_type="mrp",
                )
                session.add(mr)
                created += 1
        await session.commit()
    await _log_business_event(
        request,
        action="MRP_RUN",
        entity_type="material_request",
        summary=f"MRP run completed with {created} material request(s)",
        business_step="Material planning",
        after_value={"created": created},
    )
    return {"created": created}


# ── Supplier portal ───────────────────────────────────────────────────────────


@router.get("/supplier/dashboard", tags=["Supplier Portal"])
async def supplier_portal_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier self-service dashboard/action queue."""
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await _supplier_portal_service(request, session).dashboard(tenant_id, supplier_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.get("/supplier/profile", tags=["Supplier Portal"])
async def supplier_portal_profile(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier views its own master/profile data."""
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await _supplier_portal_service(request, session).get_profile(tenant_id, supplier_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.put("/supplier/profile", tags=["Supplier Portal"])
async def supplier_portal_update_profile(
    body: SupplierProfileUpdate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Supplier maintains contact/profile data without accessing other suppliers."""
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await _supplier_portal_service(request, session).update_profile(
                tenant_id,
                supplier_id,
                user_id,
                body.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.get("/supplier/purchase-orders", tags=["Supplier Portal"])
async def supplier_list_pos(
    request: Request,
    po_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Return only the purchase orders assigned to the authenticated supplier.

    Security guarantees:
    - supplier_id is extracted from the JWT (claim 'sid') via require_supplier_id.
    - tenant_id is extracted from the JWT (claim 'tid') via get_current_tenant_id.
    - Both filters are applied in the DB query — no client-supplied supplier_id is trusted.
    - A wrong-supplier user will always receive an empty list (not a 403, to avoid enumeration).
    """
    container = get_container(request)
    async with container.session_factory() as session:
        base_filter = [
            PurchaseOrderModel.tenant_id == tenant_id,
            PurchaseOrderModel.supplier_id == supplier_id,  # CRITICAL: JWT-derived, not user-supplied
            PurchaseOrderModel.is_deleted.is_(False),
        ]
        if po_status:
            base_filter.append(PurchaseOrderModel.status == po_status)

        # Count first for pagination metadata
        count_stmt = select(func.count(PurchaseOrderModel.id)).where(*base_filter)
        total_count = (await session.execute(count_stmt)).scalar_one()

        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(*base_filter)
            .order_by(PurchaseOrderModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        r = await session.execute(stmt)
        pos = r.scalars().unique().all()

    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "items": [_po_to_dict(p) for p in pos],
    }


@router.get("/supplier/purchase-orders/{po_id}")
async def supplier_get_po(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = (
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                PurchaseOrderModel.id == po_id,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.supplier_id == supplier_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        p = r.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="PO not found")
    return _po_to_dict(p)


@router.post(
    "/supplier/purchase-orders/{po_id}/shipment-notices",
    status_code=status.HTTP_201_CREATED,
    tags=["Supplier Portal"],
)
async def supplier_create_shipment_notice(
    po_id: uuid.UUID,
    body: SupplierShipmentNoticeCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Supplier submits an advance shipment notice for an open PO."""
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            notice = await _supplier_portal_service(request, session).create_shipping_notice(
                tenant_id,
                supplier_id,
                user_id,
                po_id,
                {
                    **body.model_dump(exclude={"lines"}, exclude_none=True),
                    "lines": [
                        {
                            "po_line_id": line.po_line_id,
                            "quantity": line.quantity,
                            "remarks": line.remarks,
                        }
                        for line in body.lines
                    ],
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    await _log_business_event(
        request,
        action="SUPPLIER_SHIPMENT_NOTICE",
        entity_type="goods_receipt_note",
        entity_id=uuid.UUID(notice["id"]),
        summary=f"Supplier shipment notice {notice['grn_number']} submitted",
        business_step="Supplier shipment",
        document_no=notice["grn_number"],
        after_value=notice,
        extra={"supplier_id": str(supplier_id), "purchase_order_id": str(po_id)},
    )
    return notice


@router.put("/supplier/purchase-orders/{po_id}/acknowledge")
async def supplier_ack_po(
    po_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        # Verify PO belongs to this supplier
        po_check = await session.get(PurchaseOrderModel, po_id)
        if not po_check or po_check.tenant_id != tenant_id or po_check.supplier_id != supplier_id or po_check.is_deleted:
            raise HTTPException(status_code=404, detail="PO not found")
        
        handler = PurchaseOrderHandler(session)
        try:
            result = await handler.acknowledge_po(po_id, tenant_id)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    await _log_business_event(
        request,
        action="PO_ACKNOWLEDGED",
        entity_type="purchase_order",
        entity_id=po_id,
        summary=f"Supplier acknowledged PO {po_check.po_number}",
        business_step="Supplier collaboration",
        document_no=po_check.po_number,
        before_value={"status": "sent"},
        after_value={"status": "acknowledged"},
        extra={"supplier_id": str(supplier_id)},
    )
    return result


@router.post("/supplier/quotations", status_code=status.HTTP_201_CREATED)
async def supplier_submit_quotation(
    body: SupplierQuotationCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        # Validate material belongs to tenant
        mat = await session.get(MaterialModel, body.material_id)
        if not mat or mat.tenant_id != tenant_id or mat.is_deleted:
            raise HTTPException(status_code=404, detail="Material not found")

        # If linked to a PO, ensure the PO exists and is assigned to this supplier and tenant
        po_uuid = _optional_uuid(body.purchase_order_id, "purchase_order_id")
        if po_uuid:
            stmt = select(PurchaseOrderModel).where(
                PurchaseOrderModel.id == po_uuid,
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.supplier_id == supplier_id,
                PurchaseOrderModel.is_deleted.is_(False),
            )
            r = await session.execute(stmt)
            po = r.scalar_one_or_none()
            if not po:
                raise HTTPException(status_code=404, detail="Purchase order not found or not assigned to this supplier")

        q = SupplierQuotationModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_order_id=po_uuid,
            material_id=body.material_id,
            quantity=float(body.quantity),
            unit_price=float(body.unit_price),
            valid_until=body.valid_until,
            status="draft",
        )
        session.add(q)
        await session.commit()
    await _log_business_event(
        request,
        action="QUOTE_CREATED",
        entity_type="supplier_quotation",
        entity_id=q.id,
        summary="Supplier quotation draft created",
        business_step="Supplier quotation",
        document_no=str(q.id),
        after_value={
            "supplier_id": str(supplier_id),
            "material_id": str(body.material_id),
            "purchase_order_id": str(po_uuid) if po_uuid else None,
            "quantity": float(body.quantity),
            "unit_price": float(body.unit_price),
            "status": "draft",
        },
    )
    return {"id": str(q.id), "status": "draft"}


@router.get("/supplier/quotations", tags=["Supplier Portal"])
async def supplier_list_quotations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier sees only its own quotations."""
    container = get_container(request)
    async with container.session_factory() as session:
        return await _supplier_portal_service(request, session).list_quotations(tenant_id, supplier_id)


@router.get("/supplier/quotations/{quotation_id}", tags=["Supplier Portal"])
async def supplier_get_quotation(
    quotation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await _supplier_portal_service(request, session).get_quotation(
                tenant_id,
                supplier_id,
                quotation_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.put(
    "/supplier/quotations/{quotation_id}/submit",
    dependencies=[Depends(require_permission("supplier:write"))],
)
async def supplier_submit_quotation_transition(
    quotation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier transitions quotation from DRAFT → SUBMITTED."""
    container = get_container(request)
    async with container.session_factory() as session:
        # Verify quotation belongs to this supplier
        q_check = await session.get(SupplierQuotationModel, quotation_id)
        if not q_check or q_check.tenant_id != tenant_id or q_check.supplier_id != supplier_id or q_check.is_deleted:
            raise HTTPException(status_code=404, detail="Quotation not found")
        
        handler = SupplierQuotationHandler(session)
        try:
            result = await handler.submit_quotation(quotation_id, tenant_id)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    await _log_business_event(
        request,
        action="QUOTE_SUBMITTED",
        entity_type="supplier_quotation",
        entity_id=quotation_id,
        summary="Supplier quotation submitted",
        business_step="Supplier quotation",
        document_no=str(quotation_id),
        before_value={"status": "draft"},
        after_value={"status": "submitted"},
        extra={"supplier_id": str(supplier_id)},
    )
    return result


@router.get("/supplier/receipts", tags=["Supplier Portal"])
async def supplier_list_receipts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        return await _supplier_portal_service(request, session).list_receipts(
            tenant_id,
            supplier_id,
            page,
            page_size,
        )


@router.get("/supplier/invoices", tags=["Supplier Portal"])
async def supplier_list_invoices(
    request: Request,
    invoice_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        return await _supplier_portal_service(request, session).list_invoices(
            tenant_id,
            supplier_id,
            invoice_status,
            page,
            page_size,
        )


@router.post("/supplier/invoices", status_code=status.HTTP_201_CREATED, tags=["Supplier Portal"])
async def supplier_create_invoice(
    body: SupplierInvoiceSubmit,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            invoice = await _supplier_portal_service(request, session).create_invoice(
                tenant_id,
                supplier_id,
                user_id,
                body.model_dump(exclude_none=True),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    await _log_business_event(
        request,
        action="SUPPLIER_INVOICE_SUBMITTED",
        entity_type="supplier_invoice",
        entity_id=uuid.UUID(invoice["id"]),
        summary=f"Supplier invoice {invoice['invoice_number']} submitted",
        business_step="Supplier invoice",
        document_no=invoice["invoice_number"],
        after_value=invoice,
        extra={"supplier_id": str(supplier_id), "purchase_order_id": invoice.get("purchase_order_id")},
    )
    return invoice


@router.get("/supplier/invoices/{invoice_id}", tags=["Supplier Portal"])
async def supplier_get_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await _supplier_portal_service(request, session).get_invoice(
                tenant_id,
                supplier_id,
                invoice_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.get("/supplier/payments", tags=["Supplier Portal"])
async def supplier_list_payments(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        return await _supplier_portal_service(request, session).list_payments(
            tenant_id,
            supplier_id,
            page,
            page_size,
        )


@router.put(
    "/quotations/{quotation_id}/approve",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def approve_quotation(
    quotation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Admin approves quotation: SUBMITTED → APPROVED."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = SupplierQuotationHandler(session)
        try:
            result = await handler.approve_quotation(quotation_id, tenant_id)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    await _log_business_event(
        request,
        action="QUOTE_APPROVED",
        entity_type="supplier_quotation",
        entity_id=quotation_id,
        summary="Supplier quotation approved",
        business_step="Supplier quotation",
        document_no=str(quotation_id),
        before_value={"status": "submitted"},
        after_value={"status": "approved"},
    )
    return result


@router.put(
    "/quotations/{quotation_id}/reject",
    dependencies=[Depends(require_permission("procurement:write"))],
)
async def reject_quotation(
    quotation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Admin rejects quotation from any state."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = SupplierQuotationHandler(session)
        try:
            result = await handler.reject_quotation(quotation_id, tenant_id)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    await _log_business_event(
        request,
        action="QUOTE_REJECTED",
        entity_type="supplier_quotation",
        entity_id=quotation_id,
        summary="Supplier quotation rejected",
        business_step="Supplier quotation",
        document_no=str(quotation_id),
        after_value={"status": "rejected"},
    )
    return result


# ── Inspection results query ─────────────────────────────────────────────────


@router.get("/quality/inspections")
async def list_inspections(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(QualityInspectionModel).where(QualityInspectionModel.tenant_id == tenant_id)
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [
        {
            "id": str(x.id),
            "reference_type": x.reference_type,
            "reference_id": str(x.reference_id),
            "result": x.result,
            "inspection_date": x.inspection_date.isoformat(),
        }
        for x in rows
    ]


# ── RFQ (Request For Quotation) ───────────────────────────────────────────────

from backend.app.application.supply_chain.rfq_service import RFQNumberService
from backend.app.application.supply_chain.supplier_performance_service import SupplierPerformanceService
from backend.app.infrastructure.persistence.models.rfq_model import (
    InvoiceDisputeModel,
    RFQLineModel,
    RFQModel,
    RFQSupplierModel,
)
from backend.app.infrastructure.persistence.models.finance_models import SupplierInvoiceModel
from backend.app.interfaces.api.v1.schemas.supply_chain_schemas import (
    InvoiceDisputeCreate,
    InvoiceDisputeResolve,
    RFQAwardRequest,
    RFQCreate,
)


def _rfq_to_dict(r: RFQModel, include_lines: bool = True) -> dict:
    d: dict = {
        "id": str(r.id),
        "rfq_number": r.rfq_number,
        "title": r.title,
        "status": r.status,
        "deadline": r.deadline.isoformat() if r.deadline else None,
        "notes": r.notes,
        "material_request_id": str(r.material_request_id) if r.material_request_id else None,
        "awarded_supplier_id": str(r.awarded_supplier_id) if r.awarded_supplier_id else None,
        "awarded_po_id": str(r.awarded_po_id) if r.awarded_po_id else None,
        "created_at": r.created_at.isoformat(),
        "supplier_invites": [
            {
                "id": str(i.id),
                "supplier_id": str(i.supplier_id),
                "status": i.status,
                "quotation_id": str(i.quotation_id) if i.quotation_id else None,
            }
            for i in r.supplier_invites
        ],
    }
    if include_lines:
        d["lines"] = [
            {
                "id": str(l.id),
                "material_id": str(l.material_id),
                "quantity": float(l.quantity),
                "description": l.description,
            }
            for l in r.lines
        ]
    return d


@router.post(
    "/rfq",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("procurement:write"))],
    tags=["RFQ"],
)
async def create_rfq(
    body: RFQCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Buyer creates a new Request For Quotation."""
    container = get_container(request)
    async with container.session_factory() as session:
        rfq_svc = RFQNumberService(session)
        rfq_number = await rfq_svc.generate(tenant_id)
        rfq = RFQModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            rfq_number=rfq_number,
            title=body.title,
            material_request_id=body.material_request_id,
            deadline=body.deadline,
            notes=body.notes,
            status="draft",
            created_by=user_id,
        )
        session.add(rfq)
        await session.flush()

        for line in body.lines:
            # CRITICAL: Validate material belongs to current tenant
            material = await session.get(MaterialModel, line.material_id)
            if not material or material.tenant_id != tenant_id or material.is_deleted:
                raise HTTPException(status_code=404, detail="Material not found")
            
            session.add(
                RFQLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    rfq_id=rfq.id,
                    material_id=line.material_id,
                    quantity=float(line.quantity),
                    description=line.description,
                )
            )

        for sid in body.supplier_ids:
            # CRITICAL: Validate supplier belongs to current tenant
            supplier = await session.get(SupplierModel, sid)
            if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
                raise HTTPException(status_code=404, detail="Supplier not found")
            
            session.add(
                RFQSupplierModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    rfq_id=rfq.id,
                    supplier_id=sid,
                    status="invited",
                )
            )

        await session.commit()
    await _log_business_event(
        request,
        action="RFQ_CREATED",
        entity_type="rfq",
        entity_id=rfq.id,
        summary=f"RFQ {rfq_number} created",
        business_step="Supplier quotation",
        document_no=rfq_number,
        after_value={
            "rfq_number": rfq_number,
            "title": body.title,
            "status": "draft",
            "line_count": len(body.lines),
            "supplier_count": len(body.supplier_ids),
            "material_request_id": str(body.material_request_id) if body.material_request_id else None,
        },
    )
    return {"id": str(rfq.id), "rfq_number": rfq_number}


@router.get("/rfq", tags=["RFQ"])
async def list_rfqs(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """List all RFQs for this tenant."""
    container = get_container(request)
    async with container.session_factory() as session:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(RFQModel)
            .options(
                selectinload(RFQModel.lines),
                selectinload(RFQModel.supplier_invites),
            )
            .where(RFQModel.tenant_id == tenant_id, RFQModel.is_deleted.is_(False))
            .order_by(RFQModel.created_at.desc())
        )
        r = await session.execute(stmt)
        rows = r.scalars().unique().all()
    return [_rfq_to_dict(row) for row in rows]


@router.get("/rfq/{rfq_id}", tags=["RFQ"])
async def get_rfq(
    rfq_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get a single RFQ with full line and supplier-invite details."""
    container = get_container(request)
    async with container.session_factory() as session:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(RFQModel)
            .options(
                selectinload(RFQModel.lines),
                selectinload(RFQModel.supplier_invites),
            )
            .where(
                RFQModel.id == rfq_id,
                RFQModel.tenant_id == tenant_id,
                RFQModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(stmt)
        rfq = r.scalar_one_or_none()
        if not rfq:
            raise HTTPException(status_code=404, detail="RFQ not found")

        # Enrich supplier invites with quotation data
        quotation_details: dict = {}
        for invite in rfq.supplier_invites:
            if invite.quotation_id:
                q = await session.get(SupplierQuotationModel, invite.quotation_id)
                if q:
                    quotation_details[str(invite.supplier_id)] = {
                        "unit_price": float(q.unit_price),
                        "quantity": float(q.quantity),
                        "valid_until": q.valid_until.isoformat() if q.valid_until else None,
                        "status": q.status,
                    }

    result = _rfq_to_dict(rfq)
    result["quotation_details"] = quotation_details
    return result


@router.post(
    "/rfq/{rfq_id}/send",
    dependencies=[Depends(require_permission("procurement:write"))],
    tags=["RFQ"],
)
async def send_rfq(
    rfq_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Send an RFQ to all invited suppliers (status: draft → sent)."""
    container = get_container(request)
    async with container.session_factory() as session:
        rfq = await session.get(RFQModel, rfq_id)
        if not rfq or rfq.tenant_id != tenant_id or rfq.is_deleted:
            raise HTTPException(status_code=404, detail="RFQ not found")
        if rfq.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft RFQs can be sent")
        rfq.status = "sent"
        rfq.updated_at = datetime.now(timezone.utc)
        await session.commit()
        rfq_number = rfq.rfq_number
    await _log_business_event(
        request,
        action="RFQ_SENT",
        entity_type="rfq",
        entity_id=rfq_id,
        summary=f"RFQ {rfq_number} sent to invited suppliers",
        business_step="Supplier quotation",
        document_no=rfq_number,
        before_value={"status": "draft"},
        after_value={"status": "sent"},
    )
    return {"status": "sent"}


@router.post(
    "/rfq/{rfq_id}/award",
    dependencies=[Depends(require_permission("procurement:write"))],
    tags=["RFQ"],
)
async def award_rfq(
    rfq_id: uuid.UUID,
    body: RFQAwardRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Award an RFQ to a supplier and auto-create a Purchase Order."""
    from decimal import Decimal

    container = get_container(request)
    async with container.session_factory() as session:
        from sqlalchemy.orm import selectinload
        rfq_stmt = (
            select(RFQModel)
            .options(selectinload(RFQModel.supplier_invites))
            .where(
                RFQModel.id == rfq_id,
                RFQModel.tenant_id == tenant_id,
                RFQModel.is_deleted.is_(False),
            )
        )
        r = await session.execute(rfq_stmt)
        rfq = r.scalar_one_or_none()
        if not rfq:
            raise HTTPException(status_code=404, detail="RFQ not found")
        if rfq.status not in ("sent", "closed"):
            raise HTTPException(status_code=400, detail="RFQ must be sent before awarding")
        if not body.lines:
            raise HTTPException(status_code=400, detail="At least one PO line required")
        
        # CRITICAL: Validate supplier was invited to this RFQ
        invited_supplier_ids = [s.supplier_id for s in rfq.supplier_invites]
        if body.supplier_id not in invited_supplier_ids:
            raise HTTPException(status_code=400, detail="Supplier not invited to this RFQ")
        
        # CRITICAL: Validate supplier belongs to current tenant (double check)
        supplier = await session.get(SupplierModel, body.supplier_id)
        if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
            raise HTTPException(status_code=404, detail="Supplier not found")

        # Generate PO
        po_svc = PONumberService(session)
        po_number = await po_svc.generate(tenant_id)
        total = Decimal("0")
        po = PurchaseOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            po_number=po_number,
            supplier_id=body.supplier_id,
            order_date=date.today(),
            expected_delivery=body.expected_delivery,
            status="draft",
            total_amount=0,
            notes=body.notes or rfq.notes,
            created_by=user_id,
        )
        session.add(po)
        await session.flush()

        for line in body.lines:
            # CRITICAL: Validate material belongs to current tenant
            material = await session.get(MaterialModel, line.material_id)
            if not material or material.tenant_id != tenant_id or material.is_deleted:
                raise HTTPException(status_code=404, detail="Material not found")
            
            lt = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
            total += lt
            session.add(
                PurchaseOrderLineModel(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    purchase_order_id=po.id,
                    material_id=line.material_id,
                    quantity=float(line.quantity),
                    received_quantity=0,
                    unit_price=float(line.unit_price),
                    line_total=float(lt),
                )
            )
        po.total_amount = float(total)

        rfq.status = "awarded"
        rfq.awarded_supplier_id = body.supplier_id
        rfq.awarded_po_id = po.id
        rfq.updated_at = datetime.now(timezone.utc)

        await session.commit()
    await _log_business_event(
        request,
        action="RFQ_AWARDED",
        entity_type="rfq",
        entity_id=rfq_id,
        summary=f"RFQ {rfq.rfq_number} awarded and PO {po_number} created",
        business_step="Purchase order",
        document_no=rfq.rfq_number,
        before_value={"status": "sent"},
        after_value={
            "status": "awarded",
            "awarded_supplier_id": str(body.supplier_id),
            "awarded_po_id": str(po.id),
            "po_number": po_number,
        },
        extra={"purchase_order_id": str(po.id), "purchase_order_no": po_number},
    )
    return {"po_id": str(po.id), "po_number": po_number}


@router.put(
    "/rfq/{rfq_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
    tags=["RFQ"],
)
async def update_rfq(
    rfq_id: uuid.UUID,
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update RFQ (only when in draft status)."""
    container = get_container(request)
    async with container.session_factory() as session:
        rfq = await session.get(RFQModel, rfq_id)
        if not rfq or rfq.tenant_id != tenant_id or rfq.is_deleted:
            raise HTTPException(status_code=404, detail="RFQ not found")
        
        # Only allow editing draft RFQs
        if rfq.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft RFQs can be edited")
        
        # Update allowed fields
        if "title" in body:
            rfq.title = body.get("title")
        if "deadline" in body:
            rfq.deadline = body.get("deadline")
        if "notes" in body:
            rfq.notes = body.get("notes")
        
        rfq.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return _rfq_to_dict(rfq)


@router.delete(
    "/rfq/{rfq_id}",
    dependencies=[Depends(require_permission("procurement:write"))],
    tags=["RFQ"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_rfq(
    rfq_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Delete RFQ (soft-delete, only when in draft status)."""
    container = get_container(request)
    async with container.session_factory() as session:
        rfq = await session.get(RFQModel, rfq_id)
        if not rfq or rfq.tenant_id != tenant_id or rfq.is_deleted:
            raise HTTPException(status_code=404, detail="RFQ not found")
        
        # Only allow deleting draft RFQs
        if rfq.status != "draft":
            raise HTTPException(status_code=400, detail="Only draft RFQs can be deleted")
        
        # Soft delete
        rfq.is_deleted = True
        rfq.deleted_at = datetime.now(timezone.utc)
        await session.commit()
    return None


# ── Supplier performance ───────────────────────────────────────────────────────


@router.get("/supplier-performance", tags=["Supplier Performance"])
async def list_supplier_performance(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Aggregate performance metrics for all active suppliers."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = SupplierPerformanceService(session)
        data = await svc.list_all_performance(tenant_id)
    return data


@router.get("/supplier-performance/{supplier_id}", tags=["Supplier Performance"])
async def get_supplier_performance(
    supplier_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Detailed performance metrics for a single supplier."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = SupplierPerformanceService(session)
        data = await svc.get_performance(tenant_id, supplier_id)
    if not data:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return data


# ── Supplier portal — RFQ view ────────────────────────────────────────────────


@router.get("/supplier/rfq", tags=["Supplier Portal"])
async def supplier_list_rfqs(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier sees RFQs they were invited to respond to."""
    container = get_container(request)
    async with container.session_factory() as session:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(RFQModel)
            .join(RFQSupplierModel, RFQSupplierModel.rfq_id == RFQModel.id)
            .options(
                selectinload(RFQModel.lines),
                selectinload(RFQModel.supplier_invites),
            )
            .where(
                RFQModel.tenant_id == tenant_id,
                RFQModel.is_deleted.is_(False),
                RFQSupplierModel.supplier_id == supplier_id,
            )
            .order_by(RFQModel.created_at.desc())
        )
        r = await session.execute(stmt)
        rows = r.scalars().unique().all()
    return [_rfq_to_dict(row) for row in rows]


@router.post("/supplier/rfq/{rfq_id}/quote", status_code=status.HTTP_201_CREATED, tags=["Supplier Portal"])
async def supplier_submit_rfq_quote(
    rfq_id: uuid.UUID,
    body: SupplierQuotationCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier submits a quotation in response to an RFQ."""
    container = get_container(request)
    async with container.session_factory() as session:
        po_uuid = _optional_uuid(body.purchase_order_id, "purchase_order_id")
        # Validate invite exists
        stmt = select(RFQSupplierModel).where(
            RFQSupplierModel.rfq_id == rfq_id,
            RFQSupplierModel.supplier_id == supplier_id,
            RFQSupplierModel.tenant_id == tenant_id,
        )
        r = await session.execute(stmt)
        invite = r.scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=403, detail="Not invited to this RFQ")

        q = SupplierQuotationModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            purchase_order_id=po_uuid,
            material_id=body.material_id,
            quantity=float(body.quantity),
            unit_price=float(body.unit_price),
            valid_until=body.valid_until,
            status="submitted",
        )
        session.add(q)
        await session.flush()

        invite.quotation_id = q.id
        invite.status = "responded"
        invite.updated_at = datetime.now(timezone.utc)

        await session.commit()
    await _log_business_event(
        request,
        action="QUOTE_SUBMITTED",
        entity_type="supplier_quotation",
        entity_id=q.id,
        summary=f"Supplier submitted quote for RFQ {rfq_id}",
        business_step="Supplier quotation",
        document_no=str(q.id),
        after_value={
            "rfq_id": str(rfq_id),
            "supplier_id": str(supplier_id),
            "material_id": str(body.material_id),
            "quantity": float(body.quantity),
            "unit_price": float(body.unit_price),
            "status": "submitted",
        },
    )
    return {"id": str(q.id)}


# ── Supplier performance (portal view) ────────────────────────────────────────


@router.get("/supplier/performance", tags=["Supplier Portal"])
async def supplier_own_performance(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier views their own performance scorecard."""
    container = get_container(request)
    async with container.session_factory() as session:
        svc = SupplierPerformanceService(session)
        data = await svc.get_performance(tenant_id, supplier_id)
    if not data:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return data


# ── Invoice disputes ───────────────────────────────────────────────────────────


@router.post(
    "/supplier/invoices/{invoice_id}/dispute",
    status_code=status.HTTP_201_CREATED,
    tags=["Supplier Portal"],
)
async def supplier_dispute_invoice(
    invoice_id: uuid.UUID,
    body: InvoiceDisputeCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """Supplier raises a dispute against a supplier invoice amount."""
    container = get_container(request)
    async with container.session_factory() as session:
        inv = await session.get(SupplierInvoiceModel, invoice_id)
        if not inv or inv.tenant_id != tenant_id or inv.is_deleted:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if inv.supplier_id != supplier_id:
            raise HTTPException(status_code=403, detail="Not your invoice")

        dispute = InvoiceDisputeModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            supplier_invoice_id=invoice_id,
            disputed_amount=float(body.disputed_amount),
            reason=body.reason,
            status="open",
            raised_by_supplier=True,
        )
        session.add(dispute)
        await session.commit()
    return {"id": str(dispute.id), "status": "open"}


@router.get("/supplier/invoices/{invoice_id}/disputes", tags=["Supplier Portal"])
async def get_invoice_disputes(
    invoice_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    supplier_id: uuid.UUID = Depends(require_supplier_id),
):
    """List all disputes for a specific invoice."""
    container = get_container(request)
    async with container.session_factory() as session:
        inv = await session.get(SupplierInvoiceModel, invoice_id)
        if not inv or inv.tenant_id != tenant_id or inv.is_deleted:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if inv.supplier_id != supplier_id:
            raise HTTPException(status_code=403, detail="Not your invoice")

        stmt = select(InvoiceDisputeModel).where(
            InvoiceDisputeModel.supplier_invoice_id == invoice_id,
            InvoiceDisputeModel.tenant_id == tenant_id,
        ).order_by(InvoiceDisputeModel.created_at.desc())
        r = await session.execute(stmt)
        rows = r.scalars().all()
    return [
        {
            "id": str(d.id),
            "disputed_amount": float(d.disputed_amount),
            "reason": d.reason,
            "status": d.status,
            "resolution_notes": d.resolution_notes,
            "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in rows
    ]


@router.put(
    "/invoices/{dispute_id}/dispute/resolve",
    dependencies=[Depends(require_permission("procurement:write"))],
    tags=["Supplier Performance"],
)
async def resolve_invoice_dispute(
    dispute_id: uuid.UUID,
    body: InvoiceDisputeResolve,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Buyer approves or rejects a supplier invoice dispute."""
    container = get_container(request)
    async with container.session_factory() as session:
        dispute = await session.get(InvoiceDisputeModel, dispute_id)
        if not dispute or dispute.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Dispute not found")
        if dispute.status != "open":
            raise HTTPException(status_code=400, detail="Dispute already resolved")

        dispute.status = body.resolution
        dispute.resolution_notes = body.resolution_notes
        dispute.resolved_by = user_id
        dispute.resolved_at = datetime.now(timezone.utc)
        dispute.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": body.resolution}

