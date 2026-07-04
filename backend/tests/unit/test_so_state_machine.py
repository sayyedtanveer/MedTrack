"""Unit tests for the SalesOrder state machine (Gap #4).

Covers:
- All 10 forward lifecycle transitions are accepted.
- Backward / invalid transitions raise InvalidStatusTransitionError.
- Exception paths DRAFT → REJECTED, any-state → CANCELLED.
- Terminal states (COMPLETED, CANCELLED, REJECTED) allow no further transitions.

Requirements: 15, 32, 37, 40 — Gap #4
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from backend.app.domain.sales.entities.sales_order import (
    SalesOrder,
    InvalidStatusTransitionError,
)
from backend.app.domain.sales.value_objects.order_status import OrderStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order(status: OrderStatus = OrderStatus.DRAFT) -> SalesOrder:
    """Return a minimal SalesOrder with a fixed status (bypasses domain init guard)."""
    order = SalesOrder(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        order_number="SO-TEST-001",
        client_id=uuid.uuid4(),
        order_date=date.today(),
        delivery_date=date.today() + timedelta(days=7),
        status=status,
    )
    return order


# ---------------------------------------------------------------------------
# 1. Forward transitions — the complete happy path
# ---------------------------------------------------------------------------

class TestForwardTransitions:
    """Every forward transition in the canonical lifecycle must succeed."""

    def test_draft_to_pending_approval(self):
        order = _make_order(OrderStatus.DRAFT)
        assert order.can_transition_to(OrderStatus.PENDING_APPROVAL)

    def test_pending_approval_to_approved(self):
        order = _make_order(OrderStatus.PENDING_APPROVAL)
        assert order.can_transition_to(OrderStatus.APPROVED)

    def test_pending_approval_to_rejected(self):
        order = _make_order(OrderStatus.PENDING_APPROVAL)
        assert order.can_transition_to(OrderStatus.REJECTED)

    def test_approved_to_confirmed(self):
        order = _make_order(OrderStatus.APPROVED)
        assert order.can_transition_to(OrderStatus.CONFIRMED)

    # Gap #4: CONFIRMED → READY_FOR_DISPATCH (FG fully reserved path)
    def test_confirmed_to_ready_for_dispatch(self):
        order = _make_order(OrderStatus.CONFIRMED)
        assert order.can_transition_to(OrderStatus.READY_FOR_DISPATCH)

    def test_ready_for_dispatch_to_shipped(self):
        order = _make_order(OrderStatus.READY_FOR_DISPATCH)
        assert order.can_transition_to(OrderStatus.SHIPPED)

    def test_shipped_to_delivered(self):
        order = _make_order(OrderStatus.SHIPPED)
        assert order.can_transition_to(OrderStatus.DELIVERED)

    # Gap #7: DELIVERED → INVOICED (auto-invoice trigger)
    def test_delivered_to_invoiced(self):
        order = _make_order(OrderStatus.DELIVERED)
        assert order.can_transition_to(OrderStatus.INVOICED)

    # Gap #4: INVOICED → PAYMENT_RECEIVED
    def test_invoiced_to_payment_received(self):
        order = _make_order(OrderStatus.INVOICED)
        assert order.can_transition_to(OrderStatus.PAYMENT_RECEIVED)

    # Gap #4 / Gap #10: PAYMENT_RECEIVED → COMPLETED
    def test_payment_received_to_completed(self):
        order = _make_order(OrderStatus.PAYMENT_RECEIVED)
        assert order.can_transition_to(OrderStatus.COMPLETED)


# ---------------------------------------------------------------------------
# 2. Action methods follow the same transitions
# ---------------------------------------------------------------------------

class TestActionMethods:
    """The action methods must update status and raise on invalid transition."""

    def test_mark_ready_for_dispatch_from_confirmed(self):
        order = _make_order(OrderStatus.CONFIRMED)
        order.mark_ready_for_dispatch()
        assert order.status == OrderStatus.READY_FOR_DISPATCH

    def test_ship_from_ready_for_dispatch(self):
        order = _make_order(OrderStatus.READY_FOR_DISPATCH)
        order.ship()
        assert order.status == OrderStatus.SHIPPED

    def test_deliver_from_shipped(self):
        order = _make_order(OrderStatus.SHIPPED)
        order.deliver()
        assert order.status == OrderStatus.DELIVERED

    def test_invoice_from_delivered(self):
        order = _make_order(OrderStatus.DELIVERED)
        order.invoice()
        assert order.status == OrderStatus.INVOICED

    def test_receive_payment_from_invoiced(self):
        order = _make_order(OrderStatus.INVOICED)
        order.receive_payment()
        assert order.status == OrderStatus.PAYMENT_RECEIVED

    def test_complete_from_payment_received(self):
        order = _make_order(OrderStatus.PAYMENT_RECEIVED)
        order.complete()
        assert order.status == OrderStatus.COMPLETED


# ---------------------------------------------------------------------------
# 3. Backward / invalid transitions raise InvalidStatusTransitionError
# ---------------------------------------------------------------------------

class TestBackwardTransitions:
    """Backward transitions MUST raise InvalidStatusTransitionError (not plain ValueError)."""

    def test_completed_to_confirmed_raises(self):
        order = _make_order(OrderStatus.COMPLETED)
        with pytest.raises(InvalidStatusTransitionError):
            order.confirm()

    def test_completed_to_shipped_raises(self):
        order = _make_order(OrderStatus.COMPLETED)
        with pytest.raises(InvalidStatusTransitionError):
            order.ship()

    def test_payment_received_to_invoiced_raises(self):
        """PAYMENT_RECEIVED → INVOICED is a backward transition."""
        order = _make_order(OrderStatus.PAYMENT_RECEIVED)
        with pytest.raises(InvalidStatusTransitionError):
            order.invoice()

    def test_invoiced_to_delivered_raises(self):
        """INVOICED → DELIVERED is a backward transition."""
        order = _make_order(OrderStatus.INVOICED)
        with pytest.raises(InvalidStatusTransitionError):
            order.deliver()

    def test_delivered_to_shipped_raises(self):
        order = _make_order(OrderStatus.DELIVERED)
        with pytest.raises(InvalidStatusTransitionError):
            order.ship()

    def test_shipped_to_confirmed_raises(self):
        order = _make_order(OrderStatus.SHIPPED)
        with pytest.raises(InvalidStatusTransitionError):
            order.confirm()

    def test_ready_for_dispatch_to_confirmed_raises(self):
        order = _make_order(OrderStatus.READY_FOR_DISPATCH)
        with pytest.raises(InvalidStatusTransitionError):
            order.confirm()

    def test_draft_to_completed_raises(self):
        order = _make_order(OrderStatus.DRAFT)
        with pytest.raises(InvalidStatusTransitionError):
            order.complete()

    def test_draft_to_invoiced_raises(self):
        order = _make_order(OrderStatus.DRAFT)
        with pytest.raises(InvalidStatusTransitionError):
            order.invoice()


# ---------------------------------------------------------------------------
# 4. Terminal states — no further transitions allowed
# ---------------------------------------------------------------------------

class TestTerminalStates:
    """COMPLETED, CANCELLED, and REJECTED are terminal — nothing else is allowed."""

    @pytest.mark.parametrize("terminal_status", [
        OrderStatus.COMPLETED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
    ])
    def test_terminal_state_allows_no_forward_transition(self, terminal_status):
        order = _make_order(terminal_status)
        # None of the forward states should be reachable
        for target in OrderStatus:
            if target != terminal_status:
                assert not order.can_transition_to(target), (
                    f"Terminal state {terminal_status} must not allow transition to {target}"
                )

    def test_cancelled_order_cannot_be_shipped(self):
        order = _make_order(OrderStatus.CANCELLED)
        with pytest.raises(InvalidStatusTransitionError):
            order.ship()

    def test_rejected_order_cannot_be_approved(self):
        order = _make_order(OrderStatus.REJECTED)
        with pytest.raises(InvalidStatusTransitionError):
            order.approve(approver_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# 5. Exception paths — CANCELLED reachable from most active states
# ---------------------------------------------------------------------------

class TestCancelPath:
    """Any active (non-terminal) state can transition to CANCELLED."""

    @pytest.mark.parametrize("active_status", [
        OrderStatus.DRAFT,
        OrderStatus.PENDING_APPROVAL,
        OrderStatus.APPROVED,
        OrderStatus.CONFIRMED,
        OrderStatus.PROCESSING,
        OrderStatus.PRODUCTION,
        OrderStatus.READY,
        OrderStatus.READY_FOR_DISPATCH,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.INVOICED,
    ])
    def test_cancel_allowed_from_active_state(self, active_status):
        order = _make_order(active_status)
        assert order.can_transition_to(OrderStatus.CANCELLED), (
            f"Expected CANCELLED to be reachable from {active_status}"
        )
        order.cancel()
        assert order.status == OrderStatus.CANCELLED


# ---------------------------------------------------------------------------
# 6. SalesOrderStatus enum completeness
# ---------------------------------------------------------------------------

class TestEnumCompleteness:
    """Verify all 10 forward states + REJECTED + CANCELLED are in the OrderStatus enum."""

    REQUIRED_STATES = {
        "DRAFT",
        "PENDING_APPROVAL",
        "APPROVED",
        "CONFIRMED",
        "READY_FOR_DISPATCH",
        "SHIPPED",
        "DELIVERED",
        "INVOICED",
        "PAYMENT_RECEIVED",
        "COMPLETED",
        "REJECTED",
        "CANCELLED",
    }

    def test_all_required_states_present(self):
        enum_names = {member.name for member in OrderStatus}
        missing = self.REQUIRED_STATES - enum_names
        assert not missing, (
            f"Missing required OrderStatus values: {missing}"
        )
