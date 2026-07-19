"""Delivery Dashboard Service - operational flow for delivery team dashboard."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel


class DeliveryDashboardService:
    """Service for delivery team operational dashboard and actions.

    Responsibilities:
    - Get dispatch queue (ready-to-ship delivery orders)
    - Get in-transit shipments
    - Get delivered orders
    - Create dispatch
    - Update shipment status
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_dispatch_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get dispatch queue for delivery dashboard (ready-to-ship)."""
        stmt = (
            select(DeliveryOrderModel)
            .where(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "READY_TO_SHIP",
                DeliveryOrderModel.is_deleted.is_(False),
            )
            .order_by(DeliveryOrderModel.shipping_date)
        )
        result = await self._session.execute(stmt)
        dos = result.scalars().all()

        dispatch_queue = []
        for do in dos:
            dispatch_queue.append({
                "delivery_order_id": do.id,
                "do_number": do.do_number,
                "customer_id": do.customer_id,
                "shipping_date": do.shipping_date,
                "priority": do.priority,
                "status": do.status,
            })

        return dispatch_queue

    async def get_in_transit_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get in-transit shipments for delivery dashboard."""
        stmt = (
            select(DeliveryOrderModel)
            .where(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "IN_TRANSIT",
                DeliveryOrderModel.is_deleted.is_(False),
            )
            .order_by(DeliveryOrderModel.shipping_date)
        )
        result = await self._session.execute(stmt)
        dos = result.scalars().all()

        in_transit_queue = []
        for do in dos:
            in_transit_queue.append({
                "delivery_order_id": do.id,
                "do_number": do.do_number,
                "customer_id": do.customer_id,
                "shipping_date": do.shipping_date,
                "priority": do.priority,
                "status": do.status,
            })

        return in_transit_queue

    async def get_delivered_queue(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get delivered orders for delivery dashboard."""
        stmt = (
            select(DeliveryOrderModel)
            .where(
                DeliveryOrderModel.tenant_id == tenant_id,
                DeliveryOrderModel.status == "DELIVERED",
                DeliveryOrderModel.is_deleted.is_(False),
            )
            .order_by(DeliveryOrderModel.shipping_date.desc())
        )
        result = await self._session.execute(stmt)
        dos = result.scalars().all()

        delivered_queue = []
        for do in dos:
            delivered_queue.append({
                "delivery_order_id": do.id,
                "do_number": do.do_number,
                "customer_id": do.customer_id,
                "shipping_date": do.shipping_date,
                "delivery_date": do.delivery_date,
                "priority": do.priority,
                "status": do.status,
            })

        return delivered_queue
