"""Delivery Dashboard REST API endpoints."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_current_user_id
from backend.app.interfaces.api.v1.dependencies.auth import get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.delivery.commands.delivery_commands import (
    CreateDispatchCommand,
    UpdateShipmentStatusCommand,
    PackDeliveryCommand,
    ConfirmDeliveryCommand,
)
from backend.app.application.delivery.handlers.delivery_dashboard_handler import DeliveryDashboardHandler


router = APIRouter(prefix="/delivery", tags=["Delivery Dashboard"])


@router.get(
    "/dispatch-queue",
    dependencies=[Depends(require_permission("delivery:dispatch:view"))],
)
async def get_dispatch_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get orders ready for dispatch (Gap #5).

    Returns sales orders in READY_FOR_DISPATCH status filtered by tenant_id.
    Each item includes: id, order_number, customer_name, grand_total, ready_at timestamp.

    Requirements: 33 — Gap #5
    Permission: delivery:dispatch:view (403 if absent)
    """
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.infrastructure.persistence.models.sales_models import (
            SalesOrderModel,
            SalesOrderLineModel,
        )

        # Query sales orders in READY_FOR_DISPATCH, filtered by tenant_id
        stmt = (
            select(SalesOrderModel)
            .where(
                and_(
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.status == "READY_FOR_DISPATCH",
                    SalesOrderModel.is_deleted.is_(False),
                )
            )
            .order_by(SalesOrderModel.delivery_date.asc())
        )
        result = await session.execute(stmt)
        sales_orders = result.scalars().all()

        queue_data = []
        for so in sales_orders:
            # ClientModel uses `name` field (not `company_name`)
            customer_name = so.client.name if so.client else None

            queue_data.append({
                "id": str(so.id),
                "order_number": so.order_number,
                "customer_name": customer_name,
                "grand_total": float(so.grand_total),
                "ready_at": so.updated_at.isoformat() if so.updated_at else None,
            })

        return queue_data


@router.get("/in-transit-queue")
async def get_in_transit_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get in-transit shipments for delivery dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_service import DeliveryService
        service = DeliveryService(session)
        queue = await service._get_in_transit_queue(tenant_id)
        return queue


@router.get("/delivered-queue")
async def get_delivered_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get delivered orders for delivery dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_service import DeliveryService
        service = DeliveryService(session)
        queue = await service._get_completed_queue(tenant_id)
        return queue


@router.get("/dashboard")
async def get_delivery_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get comprehensive delivery dashboard with all queues and metrics."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_service import DeliveryService
        service = DeliveryService(session)
        dashboard = await service.get_delivery_dashboard(tenant_id=tenant_id, user_id=user_id)
        return dashboard


@router.post("/create-dispatch", status_code=status.HTTP_200_OK)
async def create_dispatch(
    body: CreateDispatchCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create dispatch for delivery order with workflow integration."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_service import DeliveryService
        service = DeliveryService(session)
        result = await service.dispatch_order(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            tracking_number=body.tracking_number,
            dispatched_by=user_id,
        )
        await session.commit()
        return result


@router.post("/pack", status_code=status.HTTP_200_OK)
async def pack_delivery(
    body: PackDeliveryCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Pack delivery order for shipment."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = DeliveryDashboardHandler(session)
        cmd = PackDeliveryCommand(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            packed_by=user_id,
            packing_notes=body.packing_notes,
        )
        await handler.handle_pack_delivery(cmd)
        await session.commit()
        return {"status": "PACKING"}


@router.post("/update-shipment-status", status_code=status.HTTP_200_OK)
async def update_shipment_status(
    body: UpdateShipmentStatusCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update shipment status."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = DeliveryDashboardHandler(session)
        cmd = UpdateShipmentStatusCommand(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            new_status=body.new_status,
            updated_by=user_id,
            remarks=body.remarks,
        )
        await handler.handle_update_shipment_status(cmd)
        await session.commit()
        return {"status": "success"}


@router.post("/confirm-delivery", status_code=status.HTTP_200_OK)
async def confirm_delivery(
    body: ConfirmDeliveryCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Confirm delivery of order with workflow integration."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.delivery.services.delivery_service import DeliveryService
        service = DeliveryService(session)
        result = await service.confirm_delivery(
            tenant_id=tenant_id,
            delivery_order_id=body.delivery_order_id,
            delivery_notes=body.delivery_notes,
            confirmed_by=user_id,
        )
        await session.commit()
        return result
