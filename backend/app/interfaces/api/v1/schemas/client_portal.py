from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClientLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)
    tenant_id: UUID


class ClientLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    client_id: UUID
    email: str
    role: str
    full_name: str


class ClientRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ClientForgotPasswordRequest(BaseModel):
    email: str
    tenant_id: UUID


class ClientForgotPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class ClientResetPasswordRequest(BaseModel):
    token: str = Field(min_length=8)
    new_password: str = Field(min_length=8)


class ClientAddressBase(BaseModel):
    type: Literal["billing", "shipping"]
    label: Optional[str] = None
    contact_name: Optional[str] = None
    address_line1: str = Field(min_length=1)
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_default: bool = False


class ClientAddressCreateRequest(ClientAddressBase):
    pass


class ClientAddressUpdateRequest(BaseModel):
    type: Optional[Literal["billing", "shipping"]] = None
    label: Optional[str] = None
    contact_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_default: Optional[bool] = None


class ClientProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1)
    last_name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[str] = None


class ClientNotificationSettingsUpdateRequest(BaseModel):
    order_confirmed: Optional[bool] = None
    order_shipped: Optional[bool] = None
    order_delivered: Optional[bool] = None
    invoice_overdue: Optional[bool] = None
    low_credit: Optional[bool] = None
    marketing: Optional[bool] = None


class ReorderLineRequest(BaseModel):
    product_id: UUID
    product_type: str
    uom_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None


class ClientReorderRequest(BaseModel):
    order_id: UUID
    lines: Optional[List[ReorderLineRequest]] = None
    notes: Optional[str] = None


class ClientOrderCreateRequest(BaseModel):
    lines: List[ReorderLineRequest] = Field(min_length=1)
    delivery_date: Optional[date] = None
    notes: Optional[str] = None


class ClientSupportRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    message: str = Field(min_length=10, max_length=5000)


class ClientNotificationSettingResponse(BaseModel):
    order_confirmed: bool
    order_shipped: bool
    order_delivered: bool
    invoice_overdue: bool
    low_credit: bool
    marketing: bool


class ClientAddressResponse(ClientAddressBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ClientPortalNotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    message: str
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    is_read: bool
    sent_at: datetime
