"""Pydantic schemas for Sales API endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, validator


# ==================== CLIENT SCHEMAS ====================

class ClientCreateRequest(BaseModel):
    """Request to create a client."""
    code: str = Field(..., min_length=1, max_length=50, description="Unique client code")
    name: str = Field(..., min_length=1, max_length=255, description="Client name")
    email: Optional[str] = Field(None, max_length=255, description="Client email")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    address: Optional[str] = Field(None, max_length=500, description="Address")
    gst_number: Optional[str] = Field(None, max_length=50, description="GST number")
    credit_limit: Optional[Decimal] = Field(None, description="Credit limit")
    payment_terms_days: int = Field(0, ge=0, le=365, description="Payment terms in days")


class ClientUpdateRequest(BaseModel):
    """Request to update client information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    gst_number: Optional[str] = Field(None, max_length=50)
    credit_limit: Optional[Decimal] = Field(None)
    payment_terms_days: Optional[int] = Field(None, ge=0, le=365)


class ClientResponse(BaseModel):
    """Response containing client information."""
    id: UUID
    code: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    credit_used: Decimal
    payment_terms_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    """Response for listing clients."""
    items: List[ClientResponse]
    total: int
    limit: int
    offset: int


class ClientCreditCheckResponse(BaseModel):
    """Response for credit check."""
    client_id: UUID
    credit_limit: Optional[Decimal] = None
    credit_used: Decimal
    available_credit: Optional[Decimal] = None
    is_valid_for_amount: bool
    message: str


# ==================== PRICE LIST SCHEMAS ====================

class PriceListLineRequest(BaseModel):
    """Request to add/update pricing line."""
    product_id: UUID
    product_type: str = Field(..., pattern="^(variant|finished_product)$")
    unit_price: Decimal = Field(..., gt=0)


class PriceListRequest(BaseModel):
    """Request to create price list."""
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class PriceListLineResponse(BaseModel):
    """Response for price list line."""
    product_id: UUID
    product_type: str
    unit_price: Decimal

    class Config:
        from_attributes = True


class PriceListResponse(BaseModel):
    """Response for price list."""
    id: UUID
    name: str
    is_default: bool
    valid_from: date
    valid_to: Optional[date] = None
    is_active: bool
    lines: List[PriceListLineResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceListListResponse(BaseModel):
    """Response for listing price lists."""
    items: List[PriceListResponse]
    total: int
    limit: int
    offset: int


# ==================== SALES ORDER LINE SCHEMAS ====================

class SalesOrderLineCreateRequest(BaseModel):
    """Request to add line to order."""
    product_id: UUID
    product_type: str = Field(..., pattern="^(variant|finished_product)$")
    uom_id: UUID
    quantity: Decimal = Field(..., gt=0)
    tax_rate: Decimal = Field(0, ge=0, le=100)


class SalesOrderLineResponse(BaseModel):
    """Response for sales order line."""
    id: UUID
    product_id: UUID
    product_type: str
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    uom_id: UUID
    uom_code: Optional[str] = None
    uom_name: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal
    allocated_quantity: Decimal
    shipped_quantity: Decimal
    backorder_quantity: Decimal
    work_order_id: Optional[UUID] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== SALES ORDER SCHEMAS ====================

class SalesOrderCreateRequest(BaseModel):
    """Request to create a sales order."""
    client_id: UUID
    order_date: date
    delivery_date: date
    notes: Optional[str] = None

    @validator("delivery_date")
    def delivery_after_order(cls, v, values):
        """Validate delivery date is after order date."""
        if "order_date" in values and v < values["order_date"]:
            raise ValueError("Delivery date must be after order date")
        return v


class SalesOrderResponse(BaseModel):
    """Response for sales order."""
    id: UUID
    order_number: str
    client_id: UUID
    client_name: Optional[str] = None
    client_code: Optional[str] = None
    order_date: str
    delivery_date: str
    status: str
    payment_status: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    notes: Optional[str] = None
    created_by: Optional[str] = None
    approver_id: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    item_count: int = 0
    item_summary: Optional[str] = None
    lines: List[SalesOrderLineResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SalesOrderDetailResponse(BaseModel):
    """Detailed response for single order."""
    id: UUID
    order_number: str
    client: ClientResponse
    order_date: str
    delivery_date: str
    status: str
    payment_status: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    notes: Optional[str] = None
    created_by: Optional[str] = None
    approver_id: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    lines: List[SalesOrderLineResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SalesOrderListResponse(BaseModel):
    """Response for listing sales orders."""
    items: List[SalesOrderResponse]
    total: int
    limit: int
    offset: int


class ApplyDiscountRequest(BaseModel):
    """Request to apply discount to order."""
    discount_amount: Decimal = Field(..., ge=0)


class ConfirmOrderRequest(BaseModel):
    """Request to confirm order."""
    confirmed_by: str = Field(..., min_length=1, max_length=100)


class ApprovalActionRequest(BaseModel):
    """Request body for submit/approve/reject workflow actions."""
    notes: Optional[str] = Field(None, max_length=1000)


class ShipOrderRequest(BaseModel):
    """Request to ship order."""
    line_shipments: dict[str, Decimal] = Field(..., description="Map of line_id to shipped quantity")
    shipped_by: str = Field(..., min_length=1, max_length=100)


class CancelOrderRequest(BaseModel):
    """Request to cancel order."""
    reason: Optional[str] = None
    cancelled_by: Optional[str] = None


class OrderStatusResponse(BaseModel):
    """Response for order status summary."""
    DRAFT: int = 0
    PENDING_APPROVAL: int = 0
    APPROVED: int = 0
    REJECTED: int = 0
    CONFIRMED: int = 0
    PROCESSING: int = 0
    PRODUCTION: int = 0
    READY: int = 0
    SHIPPED: int = 0
    DELIVERED: int = 0
    COMPLETED: int = 0
    CANCELLED: int = 0


# ==================== ERROR SCHEMAS ====================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    message: str
    status_code: int


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: str = "validation_error"
    message: str
    details: Optional[List[dict]] = None
