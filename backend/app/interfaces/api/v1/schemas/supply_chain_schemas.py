from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    code: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst: Optional[str] = None
    payment_terms: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst: Optional[str] = None
    payment_terms: Optional[str] = None
    performance_rating: Optional[Decimal] = None
    is_active: Optional[bool] = None


class SupplierResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst: Optional[str] = None
    payment_terms: Optional[str] = None
    performance_rating: Optional[Decimal] = None
    is_active: bool

    class Config:
        from_attributes = True


class SupplierProfileUpdate(BaseModel):
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst: Optional[str] = None
    payment_terms: Optional[str] = None


class SupplierShipmentNoticeLine(BaseModel):
    po_line_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    remarks: Optional[str] = None


class SupplierShipmentNoticeCreate(BaseModel):
    lines: List[SupplierShipmentNoticeLine]
    driver_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    transport_company: Optional[str] = None
    tracking_number: Optional[str] = None
    remarks: Optional[str] = None


class SupplierInvoiceSubmit(BaseModel):
    purchase_order_id: Optional[uuid.UUID] = None
    supplier_invoice_ref: Optional[str] = None
    invoice_date: date
    due_date: date
    subtotal: Decimal = Field(gt=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    grand_total: Decimal = Field(gt=0)
    notes: Optional[str] = None


class POLineIn(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    expected_delivery: Optional[date] = None
    notes: Optional[str] = None
    lines: List[POLineIn] = Field(default_factory=list)


class ReceiveLineItem(BaseModel):
    line_id: uuid.UUID
    quantity: Decimal


class GoodsReceiptRequest(BaseModel):
    lines: List[ReceiveLineItem]
    warehouse_location_id: Optional[uuid.UUID] = None


class QualityInspectRequest(BaseModel):
    reference_type: str = "purchase_receipt"
    reference_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal
    warehouse_location_id: uuid.UUID
    result: str = Field(..., pattern="^(pass|fail|rework)$")
    remarks: Optional[str] = None
    details: Optional[List[dict]] = None


class NCRCreateRequest(BaseModel):
    inspection_id: uuid.UUID
    ncr_type: str = Field(..., pattern="^(rework|scrap|reject)$")
    reason: Optional[str] = None
    action_taken: Optional[str] = None


class SubcontractOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    product_id: uuid.UUID
    product_type: str = "variant"
    quantity: Decimal


class SubcontractIssueRequest(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal
    from_location_id: uuid.UUID
    batch_number: Optional[str] = None


class SubcontractReceiveRequest(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal
    warehouse_location_id: uuid.UUID


class SupplierQuotationCreate(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal
    valid_until: Optional[date] = None
    purchase_order_id: Optional[str] = None
    rfq_id: Optional[uuid.UUID] = None


class SupplierQuotationResponse(BaseModel):
    id: uuid.UUID
    quotation_number: str
    supplier_id: uuid.UUID
    purchase_order_id: Optional[uuid.UUID]
    material_id: uuid.UUID
    material_code: str
    material_name: str
    quantity: Decimal
    unit_price: Decimal
    valid_until: Optional[date]
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class MaterialRequestCreate(BaseModel):
    item_id: uuid.UUID
    item_type: str = Field(..., pattern="^(material|component|product)$")
    required_quantity: Decimal
    required_by: Optional[date] = None
    source_ref_type: Optional[str] = None
    source_ref_id: Optional[uuid.UUID] = None


class MaterialRequestUpdate(BaseModel):
    required_quantity: Optional[Decimal] = None
    required_by: Optional[date] = None


class MaterialRequestResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    item_type: str
    required_quantity: float
    fulfilled_quantity: float
    required_by: Optional[date] = None
    status: str
    source_ref_type: Optional[str] = None
    source_ref_id: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── RFQ schemas ───────────────────────────────────────────────────────────────

class RFQLineIn(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal
    description: Optional[str] = None


class RFQCreate(BaseModel):
    title: Optional[str] = None
    material_request_id: Optional[uuid.UUID] = None
    deadline: Optional[date] = None
    notes: Optional[str] = None
    lines: List[RFQLineIn] = Field(default_factory=list)
    supplier_ids: List[uuid.UUID] = Field(default_factory=list)


class RFQAwardRequest(BaseModel):
    supplier_id: uuid.UUID
    # Lines for the resulting PO
    lines: List[POLineIn] = Field(default_factory=list)
    expected_delivery: Optional[date] = None
    notes: Optional[str] = None


# ── Invoice dispute schemas ───────────────────────────────────────────────────

class InvoiceDisputeCreate(BaseModel):
    disputed_amount: Decimal
    reason: str


class InvoiceDisputeResolve(BaseModel):
    resolution: str = Field(..., pattern="^(approved|rejected)$")
    resolution_notes: Optional[str] = None


# ── GRN (Goods Receipt Note) Schemas ──────────────────────────────────────────

class GRNLineCreate(BaseModel):
    po_line_id: uuid.UUID
    received_quantity: Decimal
    remarks: Optional[str] = None


class GRNCreate(BaseModel):
    purchase_order_id: uuid.UUID
    warehouse_location_id: Optional[uuid.UUID] = None
    lines: List[GRNLineCreate]
    driver_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    transport_company: Optional[str] = None
    tracking_number: Optional[str] = None
    remarks: Optional[str] = None


class GRNLineResponse(BaseModel):
    id: uuid.UUID
    grn_id: uuid.UUID
    po_line_id: uuid.UUID
    material_id: uuid.UUID
    po_quantity: float
    received_quantity: float
    accepted_quantity: float
    rejected_quantity: float
    unit_price: float
    remarks: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GRNResponse(BaseModel):
    id: uuid.UUID
    grn_number: str
    purchase_order_id: uuid.UUID
    supplier_id: uuid.UUID
    status: str
    actual_receipt_date: datetime
    warehouse_location_id: Optional[uuid.UUID] = None
    driver_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    transport_company: Optional[str] = None
    tracking_number: Optional[str] = None
    remarks: Optional[str] = None
    lines: List[GRNLineResponse] = []
    created_at: datetime
    created_by: uuid.UUID

    class Config:
        from_attributes = True
