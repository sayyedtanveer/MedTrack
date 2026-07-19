"""WebSocket infrastructure for real-time notifications."""

from .connection_manager import ConnectionManager, ConnectionContext
from .event_handlers import (
    WebSocketNotificationHandler,
    OrderStatusChangeHandler,
    InventoryLowStockAlert,
    WorkOrderReleased,
    WorkOrderStarted,
    WorkOrderCompleted,
    InvoiceOverdue,
    QualityInspectionFailed,
    GeneralNotificationHandler,
)

__all__ = [
    "ConnectionManager",
    "ConnectionContext",
    "WebSocketNotificationHandler",
    "OrderStatusChangeHandler",
    "InventoryLowStockAlert",
    "WorkOrderReleased",
    "WorkOrderStarted",
    "WorkOrderCompleted",
    "InvoiceOverdue",
    "QualityInspectionFailed",
    "GeneralNotificationHandler",
]
