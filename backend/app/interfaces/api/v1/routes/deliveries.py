from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.application.delivery.delivery_service import DeliveryService
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.delivery_schemas import (
    DeliveryCancelRequest,
    DeliveryCreate,
    DeliveryResponse,
    DeliveryShipRequest,
)
from backend.app.infrastructure.logging.logger import get_logger


router = APIRouter(prefix="/deliveries", tags=["Deliveries"])
logger = get_logger(__name__)


@router.get("", response_model=list[DeliveryResponse], dependencies=[Depends(require_permission("sales:read"))])
async def list_deliveries(
    request: Request,
    sales_order_id: Optional[uuid.UUID] = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        return await DeliveryService(session).list(tenant_id, sales_order_id)


@router.post(
    "",
    response_model=DeliveryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def create_delivery(
    body: DeliveryCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            delivery = await DeliveryService(session).create_from_sales_order(
                tenant_id=tenant_id,
                sales_order_id=body.sales_order_id,
                created_by=user_id,
                lines=[line.model_dump() for line in body.lines],
                carrier=body.carrier,
                tracking_number=body.tracking_number,
                notes=body.notes,
            )
            await session.commit()
            return delivery
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            await session.rollback()
            logger.exception("Delivery creation failed", extra={"sales_order_id": str(body.sales_order_id)})
            raise


@router.get("/{delivery_id}", response_model=DeliveryResponse, dependencies=[Depends(require_permission("sales:read"))])
async def get_delivery(
    delivery_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await DeliveryService(session).get(tenant_id, delivery_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{delivery_id}/ship",
    response_model=DeliveryResponse,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def ship_delivery(
    delivery_id: uuid.UUID,
    body: DeliveryShipRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            delivery = await DeliveryService(session).ship(
                tenant_id=tenant_id,
                delivery_id=delivery_id,
                shipped_by=user_id,
                carrier=body.carrier,
                tracking_number=body.tracking_number,
            )
            await session.commit()
            return delivery
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            await session.rollback()
            logger.exception("Delivery completion failed", extra={"delivery_id": str(delivery_id)})
            raise


@router.post(
    "/{delivery_id}/deliver",
    response_model=DeliveryResponse,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def deliver_delivery(
    delivery_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            delivery = await DeliveryService(session).deliver(
                tenant_id=tenant_id,
                delivery_id=delivery_id,
                delivered_by=user_id,
            )
            await session.commit()
            return delivery
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/{delivery_id}/cancel",
    response_model=DeliveryResponse,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def cancel_delivery(
    delivery_id: uuid.UUID,
    request: Request,
    body: DeliveryCancelRequest = DeliveryCancelRequest(),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Cancel a delivery in DRAFT or PACKING status.

    Creates DISPATCH_REVERSAL inventory transactions to restore stock,
    updates SO line dispatched_quantity, creates audit log and notification.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            delivery = await DeliveryService(session).cancel(
                tenant_id=tenant_id,
                delivery_id=delivery_id,
                cancelled_by=user_id,
                reason=body.reason,
            )
            await session.commit()
            return delivery
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            await session.rollback()
            logger.exception("Delivery cancellation failed", extra={"delivery_id": str(delivery_id)})
            raise
