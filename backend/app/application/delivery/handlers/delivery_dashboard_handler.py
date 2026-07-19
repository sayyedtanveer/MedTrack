"""Delivery Dashboard Handler - orchestrates delivery operational flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.delivery.commands.delivery_commands import (
    CreateDispatchCommand,
    UpdateShipmentStatusCommand,
    PackDeliveryCommand,
    ConfirmDeliveryCommand,
)
from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel


class DeliveryDashboardHandler:
    """Handler for delivery team operational actions."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle_create_dispatch(self, cmd: CreateDispatchCommand) -> None:
        """Create dispatch for delivery order."""
        stmt = select(DeliveryOrderModel).where(
            DeliveryOrderModel.id == cmd.delivery_order_id,
            DeliveryOrderModel.tenant_id == cmd.tenant_id,
        )
        result = await self._session.execute(stmt)
        do = result.scalar_one_or_none()

        if not do:
            raise ValueError("Delivery order not found")

        if do.status != "READY_TO_SHIP":
            raise ValueError(f"Cannot dispatch order in {do.status} status")

        do.status = "IN_TRANSIT"
        do.shipped_at = datetime.now(timezone.utc)
        do.tracking_number = cmd.tracking_number
        if cmd.remarks:
            do.remarks = cmd.remarks

    async def handle_pack_delivery(self, cmd: PackDeliveryCommand) -> None:
        """Pack delivery order for shipment."""
        stmt = select(DeliveryOrderModel).where(
            DeliveryOrderModel.id == cmd.delivery_order_id,
            DeliveryOrderModel.tenant_id == cmd.tenant_id,
        )
        result = await self._session.execute(stmt)
        do = result.scalar_one_or_none()

        if not do:
            raise ValueError("Delivery order not found")

        if do.status not in ("DRAFT", "READY_TO_SHIP"):
            raise ValueError(f"Cannot pack order in {do.status} status")

        do.status = "PACKING"
        do.packed_at = datetime.now(timezone.utc)
        if cmd.packing_notes:
            do.remarks = cmd.packing_notes

    async def handle_update_shipment_status(self, cmd: UpdateShipmentStatusCommand) -> None:
        """Update shipment status."""
        stmt = select(DeliveryOrderModel).where(
            DeliveryOrderModel.id == cmd.delivery_order_id,
            DeliveryOrderModel.tenant_id == cmd.tenant_id,
        )
        result = await self._session.execute(stmt)
        do = result.scalar_one_or_none()

        if not do:
            raise ValueError("Delivery order not found")

        if cmd.new_status not in ("IN_TRANSIT", "DELIVERED"):
            raise ValueError(f"Invalid status: {cmd.new_status}")

        do.status = cmd.new_status
        if cmd.new_status == "DELIVERED":
            do.delivery_date = datetime.now(timezone.utc)
        if cmd.remarks:
            do.remarks = cmd.remarks

    async def handle_confirm_delivery(self, cmd: ConfirmDeliveryCommand) -> None:
        """Confirm delivery of order."""
        stmt = select(DeliveryOrderModel).where(
            DeliveryOrderModel.id == cmd.delivery_order_id,
            DeliveryOrderModel.tenant_id == cmd.tenant_id,
        )
        result = await self._session.execute(stmt)
        do = result.scalar_one_or_none()

        if not do:
            raise ValueError("Delivery order not found")

        if do.status != "IN_TRANSIT":
            raise ValueError(f"Cannot confirm delivery for order in {do.status} status")

        do.status = "DELIVERED"
        do.delivery_date = datetime.now(timezone.utc)
        if cmd.delivery_notes:
            do.remarks = cmd.delivery_notes
