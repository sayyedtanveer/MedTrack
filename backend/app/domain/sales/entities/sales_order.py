"""Sales Order Aggregate Root."""

from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import UUID

from backend.app.domain.shared.base_entity import AggregateRoot
from backend.app.domain.sales.value_objects import OrderNumber, OrderStatus, PaymentStatus, Money


class InvalidStatusTransitionError(Exception):
    """Raised when a Sales Order lifecycle transition is not permitted."""

    error_code = "INVALID_SO_STATUS_TRANSITION"


def _coerce_order_status(status: OrderStatus | str) -> OrderStatus:
    if isinstance(status, OrderStatus):
        return status
    status_text = str(status).upper()
    return OrderStatus.__members__.get(status_text) or OrderStatus(status_text)


class SalesOrder(AggregateRoot):
    """
    Sales Order - Aggregate Root for order management.
    
    Responsibilities:
    - Order lifecycle management (status transitions)
    - Line items collection
    - Totals calculation and validation
    - Business rule enforcement
    """

    def __init__(
        self,
        id: UUID,
        tenant_id: UUID,
        order_number: OrderNumber | str,
        client_id: UUID,
        order_date: date | str,
        delivery_date: date | str,
        status: OrderStatus | str = OrderStatus.DRAFT,
        payment_status: PaymentStatus | str = PaymentStatus.PENDING,
        subtotal: Decimal | int | float | str = Decimal("0"),
        discount_amount: Decimal | int | float | str = Decimal("0"),
        tax_amount: Decimal | int | float | str = Decimal("0"),
        grand_total: Decimal | int | float | str = Decimal("0"),
        notes: str | None = None,
        created_by: str | None = None,
        approver_id: UUID | None = None,
        submitted_at: datetime | None = None,
        approved_at: datetime | None = None,
        rejected_at: datetime | None = None,
        approval_notes: str | None = None,
        lines: list | None = None,
        is_active: bool = True,
        is_deleted: bool = False,
        deleted_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        """Initialize Sales Order."""
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        
        # Order identity
        if isinstance(order_number, OrderNumber):
            self.order_number = order_number
        else:
            try:
                self.order_number = OrderNumber(order_number)
            except ValueError:
                # Older/demo rows may use business-friendly numbers outside the SO-* pattern.
                self.order_number = order_number
        self.client_id = client_id
        self.order_date = date.fromisoformat(order_date) if isinstance(order_date, str) else order_date
        self.delivery_date = date.fromisoformat(delivery_date) if isinstance(delivery_date, str) else delivery_date
        
        # Status
        self.status = _coerce_order_status(status)
        self.payment_status = (
            payment_status if isinstance(payment_status, PaymentStatus) else PaymentStatus(str(payment_status).lower())
        )
        
        # Totals (denormalized for efficiency)
        self.subtotal = Decimal(str(subtotal))
        self.discount_amount = Decimal(str(discount_amount))
        self.tax_amount = Decimal(str(tax_amount))
        self.grand_total = Decimal(str(grand_total))
        
        # Content
        self.lines: list = lines or []  # List[SalesOrderLine]
        self.notes = notes
        self.created_by = created_by
        self.approver_id = approver_id
        self.submitted_at = submitted_at
        self.approved_at = approved_at
        self.rejected_at = rejected_at
        self.approval_notes = approval_notes
        self.is_active = is_active
        
        self._validate()

    def _validate(self) -> None:
        """Validate order invariants."""
        if self.delivery_date < self.order_date:
            raise ValueError("Delivery date cannot be before order date")
        if not self.order_number:
            raise ValueError("Order number is required")

    def add_line(self, line) -> None:
        """
        Add a line to the order.
        
        Args:
            line: SalesOrderLine instance
            
        Raises:
            ValueError: If order not in DRAFT status
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError("Cannot add lines to non-draft orders")
        self.lines.append(line)
        self._recalculate_totals()

    def remove_line(self, line_id: UUID) -> None:
        """
        Remove a line from the order.
        
        Args:
            line_id: Line ID to remove
            
        Raises:
            ValueError: If order not in DRAFT status or line not found
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError("Cannot remove lines from non-draft orders")
        
        original_count = len(self.lines)
        self.lines = [line for line in self.lines if line.id != line_id]
        
        if len(self.lines) == original_count:
            raise ValueError(f"Line {line_id} not found")
        
        self._recalculate_totals()

    def apply_discount(self, discount_amount: Decimal) -> None:
        """
        Apply discount to order.
        
        Args:
            discount_amount: Discount amount
            
        Raises:
            ValueError: If discount exceeds subtotal or order not in DRAFT
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError("Cannot modify non-draft orders")
        
        discount_amount = Decimal(str(discount_amount))
        if discount_amount < 0:
            raise ValueError("Discount cannot be negative")
        if discount_amount > self.subtotal:
            raise ValueError("Discount cannot exceed subtotal")
        
        self.discount_amount = discount_amount
        self._recalculate_totals()

    def _recalculate_totals(self) -> None:
        """Recalculate order totals from lines."""
        from decimal import Decimal
        
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        
        for line in self.lines:
            line._calculate_totals()  # Ensure line totals are fresh
            subtotal += line.quantity * line.unit_price
            tax_total += line.tax_amount
        
        self.subtotal = subtotal.quantize(Decimal("0.01"))
        self.tax_amount = tax_total.quantize(Decimal("0.01"))
        
        # Grand total = subtotal - discount + tax
        self.grand_total = (
            self.subtotal - self.discount_amount + self.tax_amount
        ).quantize(Decimal("0.01"))

    # Canonical forward-transition map — single source of truth for this aggregate.
    # Any state not listed here has no valid forward transitions (terminal states).
    VALID_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
        OrderStatus.DRAFT: [
            OrderStatus.PENDING_APPROVAL,
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.PENDING_APPROVAL: [
            OrderStatus.APPROVED,
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.APPROVED: [
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.REJECTED: [],
        # CONFIRMED → READY_FOR_DISPATCH (Gap #4): FG fully reserved path
        # CONFIRMED → PROCESSING / PRODUCTION: production-required path
        OrderStatus.CONFIRMED: [
            OrderStatus.READY_FOR_DISPATCH,
            OrderStatus.PROCESSING,
            OrderStatus.PRODUCTION,
            OrderStatus.READY,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.PROCESSING: [
            OrderStatus.PRODUCTION,
            OrderStatus.READY,
            OrderStatus.READY_FOR_DISPATCH,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.PRODUCTION: [
            OrderStatus.READY,
            OrderStatus.READY_FOR_DISPATCH,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.READY: [
            OrderStatus.READY_FOR_DISPATCH,
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED,
        ],
        # READY_FOR_DISPATCH → SHIPPED
        OrderStatus.READY_FOR_DISPATCH: [
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED,
        ],
        # SHIPPED → DELIVERED
        OrderStatus.SHIPPED: [
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
        ],
        # DELIVERED → INVOICED (Gap #7 auto-invoice trigger)
        OrderStatus.DELIVERED: [
            OrderStatus.INVOICED,
            OrderStatus.CANCELLED,
        ],
        # INVOICED → PAYMENT_RECEIVED (Gap #4)
        OrderStatus.INVOICED: [
            OrderStatus.PAYMENT_RECEIVED,
            OrderStatus.CANCELLED,
        ],
        # PAYMENT_RECEIVED → COMPLETED (Gap #4 / Gap #10)
        OrderStatus.PAYMENT_RECEIVED: [
            OrderStatus.COMPLETED,
        ],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: [],
    }

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """Return True if transitioning from current status to *new_status* is allowed."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def submit_for_approval(self, approver_id: UUID | None = None) -> None:
        """Move a draft order into the manager approval queue."""
        if not self.can_transition_to(OrderStatus.PENDING_APPROVAL):
            raise InvalidStatusTransitionError(
                f"Cannot submit order in {self.status.value} status for approval"
            )
        if not self.lines:
            raise ValueError("Cannot submit order with no lines")

        self.status = OrderStatus.PENDING_APPROVAL
        self.approver_id = approver_id
        self.submitted_at = datetime.now(timezone.utc)
        self._touch()

    def approve(self, approver_id: UUID, notes: str | None = None) -> None:
        """Approve a submitted order before execution."""
        if not self.can_transition_to(OrderStatus.APPROVED):
            raise InvalidStatusTransitionError(f"Cannot approve order in {self.status.value} status")

        self.status = OrderStatus.APPROVED
        self.approver_id = approver_id
        self.approved_at = datetime.now(timezone.utc)
        self.rejected_at = None
        self.approval_notes = notes
        self._touch()

    def reject(self, approver_id: UUID, notes: str | None = None) -> None:
        """Reject a submitted order and stop execution."""
        if not self.can_transition_to(OrderStatus.REJECTED):
            raise InvalidStatusTransitionError(f"Cannot reject order in {self.status.value} status")

        self.status = OrderStatus.REJECTED
        self.approver_id = approver_id
        self.rejected_at = datetime.now(timezone.utc)
        self.approval_notes = notes
        self._touch()

    def confirm(self) -> None:
        """
        Confirm order (transition from APPROVED → CONFIRMED).

        Raises:
            InvalidStatusTransitionError: If status transition is invalid.
            ValueError: If order has no lines.
        """
        if not self.can_transition_to(OrderStatus.CONFIRMED):
            raise InvalidStatusTransitionError(
                f"Cannot confirm order in {self.status.value} status"
            )
        if not self.lines:
            raise ValueError("Cannot confirm order with no lines")

        self.status = OrderStatus.CONFIRMED
        self._touch()

    def transition_to_production(self) -> None:
        """Transition order to PRODUCTION status."""
        if not self.can_transition_to(OrderStatus.PRODUCTION):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to PRODUCTION"
            )
        self.status = OrderStatus.PRODUCTION
        self._touch()

    def transition_to_ready(self) -> None:
        """Transition order to READY status."""
        if not self.can_transition_to(OrderStatus.READY):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to READY"
            )
        self.status = OrderStatus.READY
        self._touch()

    def mark_ready_for_dispatch(self) -> None:
        """Transition order to READY_FOR_DISPATCH (Gap #4 — all lines allocated)."""
        if not self.can_transition_to(OrderStatus.READY_FOR_DISPATCH):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to READY_FOR_DISPATCH"
            )
        self.status = OrderStatus.READY_FOR_DISPATCH
        self._touch()

    def ship(self) -> None:
        """Transition order to SHIPPED status."""
        if not self.can_transition_to(OrderStatus.SHIPPED):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to SHIPPED"
            )
        self.status = OrderStatus.SHIPPED
        self._touch()

    def deliver(self) -> None:
        """Transition order to DELIVERED status."""
        if not self.can_transition_to(OrderStatus.DELIVERED):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to DELIVERED"
            )
        self.status = OrderStatus.DELIVERED
        self._touch()

    def invoice(self) -> None:
        """Transition order to INVOICED status (Gap #4 / Gap #7 auto-invoice)."""
        if not self.can_transition_to(OrderStatus.INVOICED):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to INVOICED"
            )
        self.status = OrderStatus.INVOICED
        self._touch()

    def receive_payment(self) -> None:
        """Transition order to PAYMENT_RECEIVED status (Gap #4)."""
        if not self.can_transition_to(OrderStatus.PAYMENT_RECEIVED):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to PAYMENT_RECEIVED"
            )
        self.status = OrderStatus.PAYMENT_RECEIVED
        self._touch()

    def complete(self) -> None:
        """Transition order to COMPLETED status (Gap #4 / Gap #10)."""
        if not self.can_transition_to(OrderStatus.COMPLETED):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {self.status.value} to COMPLETED"
            )
        self.status = OrderStatus.COMPLETED
        self._touch()

    def cancel(self) -> None:
        """Cancel order if allowed."""
        if not self.can_transition_to(OrderStatus.CANCELLED):
            raise InvalidStatusTransitionError(
                f"Cannot cancel order in {self.status.value} status"
            )
        self.status = OrderStatus.CANCELLED
        self._touch()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "order_number": str(self.order_number),
            "client_id": str(self.client_id),
            "client_name": getattr(self, "client_name", None),
            "client_code": getattr(self, "client_code", None),
            "order_date": self.order_date.isoformat(),
            "delivery_date": self.delivery_date.isoformat(),
            "status": self.status.name,
            "payment_status": self.payment_status.name,
            "subtotal": str(self.subtotal),
            "discount_amount": str(self.discount_amount),
            "tax_amount": str(self.tax_amount),
            "grand_total": str(self.grand_total),
            "item_count": len(self.lines),
            "item_summary": getattr(self, "item_summary", None),
            "lines": [line.to_dict() for line in self.lines],
            "notes": self.notes,
            "created_by": self.created_by,
            "approver_id": str(self.approver_id) if self.approver_id else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "approval_notes": self.approval_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

