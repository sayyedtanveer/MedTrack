from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeliveryLineCreate(BaseModel):
    sales_order_line_id: UUID
    quantity: Decimal = Field(gt=0)


class DeliveryCreate(BaseModel):
    sales_order_id: UUID
    lines: List[DeliveryLineCreate] = Field(default_factory=list)
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class DeliveryShipRequest(BaseModel):
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None


class DeliveryCancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class DeliveryLineResponse(BaseModel):
    id: UUID
    sales_order_line_id: UUID
    variant_id: UUID
    quantity: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class DeliveryResponse(BaseModel):
    id: UUID
    delivery_number: str
    sales_order_id: UUID
    status: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[UUID] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None
    lines: List[DeliveryLineResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
