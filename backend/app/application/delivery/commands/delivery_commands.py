"""Commands for Delivery operational flow."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class CreateDispatchCommand(BaseModel):
    tenant_id: uuid.UUID
    delivery_order_id: uuid.UUID
    shipped_by: uuid.UUID
    tracking_number: Optional[str] = None
    remarks: Optional[str] = None


class UpdateShipmentStatusCommand(BaseModel):
    tenant_id: uuid.UUID
    delivery_order_id: uuid.UUID
    new_status: str  # "IN_TRANSIT", "DELIVERED"
    updated_by: uuid.UUID
    remarks: Optional[str] = None


class PackDeliveryCommand(BaseModel):
    """Pack delivery order for shipment."""
    tenant_id: uuid.UUID
    delivery_order_id: uuid.UUID
    packed_by: uuid.UUID
    packing_notes: Optional[str] = None


class ConfirmDeliveryCommand(BaseModel):
    tenant_id: uuid.UUID
    delivery_order_id: uuid.UUID
    confirmed_by: uuid.UUID
    delivery_notes: Optional[str] = None
