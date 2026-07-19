"""WebSocket event handlers for broadcasting domain events to connected clients."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.app.domain.shared.domain_event import DomainEvent
from backend.app.infrastructure.events.event_handler_interface import IEventHandler
from backend.app.infrastructure.websocket.connection_manager import ConnectionManager
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class WebSocketNotificationHandler(IEventHandler):
    """
    Base handler for broadcasting domain events to WebSocket clients.
    
    Subscribes to specific domain events and broadcasts them to relevant users
    via the ConnectionManager.
    """

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._connection_manager = connection_manager

    @property
    def event_type(self) -> str:
        """Override in subclasses to specify event type."""
        raise NotImplementedError

    async def handle(self, event: DomainEvent) -> None:
        """Process domain event and broadcast to clients."""
        raise NotImplementedError

    def _create_notification(
        self,
        event_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: dict = None,
    ) -> dict:
        """Create a standardized notification payload."""
        return {
            "id": event_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class OrderStatusChangeHandler(WebSocketNotificationHandler):
    """Handle order status change events."""

    @property
    def event_type(self) -> str:
        return "order.status_changed"

    async def handle(self, event: DomainEvent) -> None:
        order_id = str(getattr(event, "order_id", event.aggregate_id))
        status = getattr(event, "status", "UNKNOWN")
        order_number = getattr(event, "order_number", "")

        notification = self._create_notification(
            event_id=str(event.event_id),
            notification_type="ORDER_STATUS_CHANGED",
            title="Order Status Updated",
            message=f"Order {order_number} status changed to {status}",
            data={
                "order_id": order_id,
                "status": status,
                "order_number": order_number,
            },
        )

        # Broadcast to tenant
        await self._connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification,
        )

        logger.debug(
            "Broadcasted order status change",
            extra={"order_id": order_id, "status": status},
        )


class InventoryLowStockAlert(WebSocketNotificationHandler):
    """Handle low stock alert events."""

    @property
    def event_type(self) -> str:
        return "inventory.low_stock_alert"

    async def handle(self, event: DomainEvent) -> None:
        material_id = str(getattr(event, "material_id", event.aggregate_id))
        material_code = getattr(event, "material_code", "")
        current_stock = getattr(event, "current_stock", 0)
        reorder_level = getattr(event, "reorder_level", 0)

        notification = self._create_notification(
            event_id=str(event.event_id),
            notification_type="LOW_STOCK",
            title="Low Stock Alert",
            message=f"{material_code} stock ({current_stock}) below reorder level ({reorder_level})",
            data={
                "material_id": material_id,
                "material_code": material_code,
                "current_stock": current_stock,
                "reorder_level": reorder_level,
            },
        )

        # Broadcast to tenant (storekeepers, managers)
        await self._connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification,
        )

        logger.debug(
            "Broadcasted low stock alert",
            extra={"material_code": material_code, "stock": current_stock},
        )


class WorkOrderReleased(WebSocketNotificationHandler):
    """Handle work order released events."""

    @property
    def event_type(self) -> str:
        return "work_order.released"

    async def handle(self, event: DomainEvent) -> None:
        wo_id = str(getattr(event, "wo_id", event.aggregate_id))
        wo_number = getattr(event, "wo_number", "")
        product = getattr(event, "product", "")

        notification = self._create_notification(
            event_id=str(event.event_id),
            notification_type="WORK_ORDER_RELEASED",
            title="Work Order Released",
            message=f"Work Order {wo_number} for {product} has been released",
            data={
                "work_order_id": wo_id,
                "wo_number": wo_number,
                "product": product,
            },
        )

        await self._connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification,
        )

        logger.debug(
            "Broadcasted work order released",
            extra={"wo_number": wo_number},
        )


class WorkOrderStarted(WebSocketNotificationHandler):
    """Handle work order started events."""

    @property
    def event_type(self) -> str:
        return "work_order.started"

    async def handle(self, event: DomainEvent) -> None:
        wo_id = str(getattr(event, "wo_id", event.aggregate_id))
        wo_number = getattr(event, "wo_number", "")
        operator = getattr(event, "operator_name", "")

        notification = self._create_notification(
            event_id=str(event.event_id),
            notification_type="WORK_ORDER_STARTED",
            title="Work Order Started",
            message=f"Work Order {wo_number} started by {operator}" if operator else f"Work Order {wo_number} has started",
            data={
                "work_order_id": wo_id,
                "wo_number": wo_number,
                "operator": operator,
            },
        )

        await self._connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification,
        )

        logger.debug("Broadcasted work order started", extra={"wo_number": wo_number})


class WorkOrderCompleted(WebSocketNotificationHandler):
    """Handle work order completed events."""

    @property
    def event_type(self) -> str:
        return "work_order.completed"

    async def handle(self, event: DomainEvent) -> None:
        wo_id = str(getattr(event, "wo_id", event.aggregate_id))
        wo_number = getattr(event, "wo_number", "")
        produced_qty = getattr(event, "produced_qty", 0)

        notification = self._create_notification(
            event_id=str(event.event_id),
            notification_type="WORK_ORDER_COMPLETED",
            title="Work Order Completed",
            message=f"Work Order {wo_number} completed with {produced_qty} units produced",
            data={
                "work_order_id": wo_id,
                "wo_number": wo_number,
                "produced_qty": produced_qty,
            },
        )

        await self._connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification,
        )

        logger.debug("Broadcasted work order completed", extra={"wo_number": wo_number})


class InvoiceOverdue(WebSocketNotificationHandler):
    """Handle invoice overdue events."""

    @property
    def event_type(self) -> str:
        return "invoice.overdue"

    async def handle(self, event: DomainEvent) -> None:
        invoice_id = str(getattr(event, "invoice_id", event.aggregate_id))
        invoice_number = getattr(event, "invoice_number", "")
        client_name = getattr(event, "client_name", "")
        days_overdue = getattr(event, "days_overdue", 0)

        notification = self._create_notification(
            event_id=str(event.event_id),
            notification_type="INVOICE_OVERDUE",
            title="Invoice Overdue",
            message=f"Invoice {invoice_number} from {client_name} is {days_overdue} days overdue",
            data={
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "client_name": client_name,
                "days_overdue": days_overdue,
            },
        )

        await self._connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification,
        )

        logger.debug("Broadcasted invoice overdue", extra={"invoice_number": invoice_number})


class QualityInspectionFailed(WebSocketNotificationHandler):
    """Handle quality inspection failed events."""

    @property
    def event_type(self) -> str:
        return "quality.inspection_failed"

    async def handle(self, event: DomainEvent) -> None:
        inspection_id = str(getattr(event, "inspection_id", event.aggregate_id))
        material = getattr(event, "material", "")
        reason = getattr(event, "failure_reason", "Quality check failed")

        notification = self._create_notification(
            event_id=str(event.event_id),
            notification_type="QUALITY_INSPECTION_FAILED",
            title="Quality Inspection Failed",
            message=f" Quality inspection failed for {material}: {reason}",
            data={
                "inspection_id": inspection_id,
                "material": material,
                "failure_reason": reason,
            },
        )

        await self._connection_manager.broadcast_to_tenant(
            tenant_id=event.tenant_id,
            message_type="notification",
            payload=notification,
        )

        logger.debug(
            "Broadcasted quality inspection failed",
            extra={"material": material},
        )


class GeneralNotificationHandler(WebSocketNotificationHandler):
    """
    Fallback handler for any unhandled domain events.
    Broadcasts to tenant with generic notification type.
    """

    @property
    def event_type(self) -> str:
        return "*"  # Subscribe to all events

    async def handle(self, event: DomainEvent) -> None:
        # Only handle if no specific handler caught it
        # For now, just log it
        logger.debug(
            "General notification handler received event",
            extra={
                "event_type": event.event_type,
                "tenant_id": str(event.tenant_id),
            },
        )
