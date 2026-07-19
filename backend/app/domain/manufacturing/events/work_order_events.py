"""Domain events for Work Order lifecycle transitions."""
from dataclasses import dataclass
from uuid import UUID
from backend.app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True)
class WorkOrderCreated(DomainEvent):
    """Event raised when a work order is created."""
    wo_id: str
    wo_number: str
    product_id: str
    bom_id: str
    planned_quantity: float


@dataclass(frozen=True)
class WorkOrderReleased(DomainEvent):
    """Event raised when a work order is released (can consume materials)."""
    wo_id: str
    wo_number: str
    product: str


@dataclass(frozen=True)
class WorkOrderStarted(DomainEvent):
    """Event raised when a work order begins production."""
    wo_id: str
    wo_number: str
    operator_name: str = ""


@dataclass(frozen=True)
class WorkOrderCompleted(DomainEvent):
    """Event raised when a work order completes production."""
    wo_id: str
    wo_number: str
    produced_qty: float


@dataclass(frozen=True)
class WorkOrderClosed(DomainEvent):
    """Event raised when a work order is closed."""
    wo_id: str
    wo_number: str
