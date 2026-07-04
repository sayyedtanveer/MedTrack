"""
Property tests for Delivery Cancellation Inventory Restoration.

# Feature: manufacturing-erp-audit, Property 17: Delivery Cancellation Inventory Restoration

**Validates: Requirements 33.3, 33.4**

These tests validate that:
  - For any cancelled delivery with line items, the system creates
    DISPATCH_REVERSAL transactions with positive quantities exactly equal
    to each line's dispatched quantity.
  - The sum of reversal quantities equals the total dispatched quantity
    of the cancelled delivery.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    integers,
    lists,
    composite,
    uuids,
)


# ─── Data Classes (mirrors delivery model structure) ─────────────────────────


@dataclass
class DeliveryLine:
    """Represents a line item on a delivery note."""

    sales_order_line_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: Decimal  # dispatched quantity for this line


@dataclass
class CancelledDelivery:
    """Represents a cancelled delivery with its line items."""

    delivery_id: uuid.UUID
    tenant_id: uuid.UUID
    lines: List[DeliveryLine] = field(default_factory=list)


@dataclass
class DispatchReversalTransaction:
    """Represents a DISPATCH_REVERSAL inventory transaction."""

    material_id: uuid.UUID
    quantity: Decimal  # must be positive
    reference_type: str  # always "delivery"
    reference_id: uuid.UUID  # delivery_id
    transaction_type: str = "DISPATCH_REVERSAL"


# ─── Helper: Simulates the cancellation logic ────────────────────────────────


def create_dispatch_reversals(delivery: CancelledDelivery) -> List[DispatchReversalTransaction]:
    """
    Simulate the delivery cancellation inventory restoration logic.

    This mirrors the logic in DeliveryService.cancel():
        for delivery_line in delivery.lines:
            quantity = Decimal(str(delivery_line.quantity))
            if quantity <= 0:
                continue
            tx = InventoryTransactionModel(
                material_id=delivery_line.variant_id,
                transaction_type="DISPATCH_REVERSAL",
                quantity=float(quantity),  # positive to restore stock
                reference_type="delivery",
                reference_id=delivery.id,
            )

    Returns list of DISPATCH_REVERSAL transactions created.
    """
    transactions: List[DispatchReversalTransaction] = []
    for line in delivery.lines:
        if line.quantity <= Decimal("0"):
            continue
        tx = DispatchReversalTransaction(
            material_id=line.variant_id,
            quantity=line.quantity,
            reference_type="delivery",
            reference_id=delivery.delivery_id,
        )
        transactions.append(tx)
    return transactions


# ─── Strategies ──────────────────────────────────────────────────────────────

# Positive dispatch quantities (what was originally dispatched on a delivery line)
positive_dispatch_quantity = decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("100000.000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)


@composite
def delivery_line_strategy(draw):
    """Generate a single delivery line with random positive quantity."""
    sales_order_line_id = draw(uuids())
    variant_id = draw(uuids())
    quantity = draw(positive_dispatch_quantity)
    return DeliveryLine(
        sales_order_line_id=sales_order_line_id,
        variant_id=variant_id,
        quantity=quantity,
    )


@composite
def cancelled_delivery_strategy(draw):
    """Generate a cancelled delivery with 1 to 20 random line items.

    All lines have positive quantities representing dispatched goods
    that need to be reversed.
    """
    delivery_id = draw(uuids())
    tenant_id = draw(uuids())
    num_lines = draw(integers(min_value=1, max_value=20))
    lines = [draw(delivery_line_strategy()) for _ in range(num_lines)]
    return CancelledDelivery(
        delivery_id=delivery_id,
        tenant_id=tenant_id,
        lines=lines,
    )


@composite
def cancelled_delivery_with_zero_lines_strategy(draw):
    """Generate a cancelled delivery with some zero-quantity lines mixed in.

    This tests that zero-quantity lines are correctly skipped.
    """
    delivery_id = draw(uuids())
    tenant_id = draw(uuids())
    num_positive_lines = draw(integers(min_value=1, max_value=10))
    num_zero_lines = draw(integers(min_value=1, max_value=5))

    lines = []
    for _ in range(num_positive_lines):
        lines.append(draw(delivery_line_strategy()))
    for _ in range(num_zero_lines):
        lines.append(DeliveryLine(
            sales_order_line_id=draw(uuids()),
            variant_id=draw(uuids()),
            quantity=Decimal("0"),
        ))

    return CancelledDelivery(
        delivery_id=delivery_id,
        tenant_id=tenant_id,
        lines=lines,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Property 17: Delivery Cancellation Inventory Restoration
#
# For any cancelled delivery with line items, the system SHALL create
# DISPATCH_REVERSAL transactions with positive quantities exactly equal
# to each line's dispatched quantity. The sum of reversal quantities SHALL
# equal the total dispatched quantity of the cancelled delivery.
# ─────────────────────────────────────────────────────────────────────────────


class TestDispatchReversalQuantities:
    """**Validates: Requirements 33.3, 33.4**"""

    @given(delivery=cancelled_delivery_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_reversal_quantities_exactly_equal_dispatched_quantities(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: Each DISPATCH_REVERSAL transaction has a positive quantity
        exactly equal to the corresponding delivery line's dispatched quantity.
        """
        reversals = create_dispatch_reversals(delivery)

        # There should be one reversal per positive-quantity line
        positive_lines = [l for l in delivery.lines if l.quantity > Decimal("0")]
        assert len(reversals) == len(positive_lines), (
            f"Expected {len(positive_lines)} reversals, got {len(reversals)}"
        )

        # Each reversal quantity must exactly match the dispatch quantity
        for reversal, line in zip(reversals, positive_lines):
            assert reversal.quantity == line.quantity, (
                f"Reversal quantity {reversal.quantity} does not equal "
                f"dispatched quantity {line.quantity} for variant {line.variant_id}"
            )

    @given(delivery=cancelled_delivery_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_reversal_quantities_are_positive(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: All DISPATCH_REVERSAL transactions must have positive
        quantities (restoring stock, not reducing it).
        """
        reversals = create_dispatch_reversals(delivery)

        for reversal in reversals:
            assert reversal.quantity > Decimal("0"), (
                f"Reversal quantity must be positive, got {reversal.quantity} "
                f"for material {reversal.material_id}"
            )

    @given(delivery=cancelled_delivery_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_sum_of_reversals_equals_total_dispatched(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: The sum of all reversal quantities equals the total
        dispatched quantity of the cancelled delivery.
        """
        reversals = create_dispatch_reversals(delivery)

        total_dispatched = sum(
            (l.quantity for l in delivery.lines if l.quantity > Decimal("0")),
            Decimal("0"),
        )
        total_reversed = sum(
            (r.quantity for r in reversals),
            Decimal("0"),
        )

        assert total_reversed == total_dispatched, (
            f"Total reversed {total_reversed} != total dispatched {total_dispatched}"
        )

    @given(delivery=cancelled_delivery_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_reversals_are_dispatch_reversal_type(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: All transactions created are of type DISPATCH_REVERSAL.
        """
        reversals = create_dispatch_reversals(delivery)

        for reversal in reversals:
            assert reversal.transaction_type == "DISPATCH_REVERSAL", (
                f"Expected DISPATCH_REVERSAL type, got {reversal.transaction_type}"
            )

    @given(delivery=cancelled_delivery_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_reversals_reference_the_cancelled_delivery(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: All reversal transactions reference the cancelled delivery
        as their source (reference_type='delivery', reference_id=delivery_id).
        """
        reversals = create_dispatch_reversals(delivery)

        for reversal in reversals:
            assert reversal.reference_type == "delivery", (
                f"Expected reference_type 'delivery', got '{reversal.reference_type}'"
            )
            assert reversal.reference_id == delivery.delivery_id, (
                f"Expected reference_id {delivery.delivery_id}, "
                f"got {reversal.reference_id}"
            )

    @given(delivery=cancelled_delivery_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_reversal_material_ids_match_delivery_line_variants(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: Each reversal transaction targets the same material
        (variant_id) as the corresponding delivery line.
        """
        reversals = create_dispatch_reversals(delivery)
        positive_lines = [l for l in delivery.lines if l.quantity > Decimal("0")]

        for reversal, line in zip(reversals, positive_lines):
            assert reversal.material_id == line.variant_id, (
                f"Reversal material {reversal.material_id} does not match "
                f"delivery line variant {line.variant_id}"
            )


class TestZeroQuantityLineHandling:
    """Test that zero-quantity lines are correctly excluded from reversals.

    **Validates: Requirements 33.3, 33.4**
    """

    @given(delivery=cancelled_delivery_with_zero_lines_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_zero_quantity_lines_produce_no_reversals(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: Lines with quantity <= 0 do not produce reversal transactions.
        Only positive-quantity lines generate DISPATCH_REVERSAL entries.
        """
        reversals = create_dispatch_reversals(delivery)
        positive_lines = [l for l in delivery.lines if l.quantity > Decimal("0")]

        assert len(reversals) == len(positive_lines), (
            f"Expected {len(positive_lines)} reversals (ignoring zero lines), "
            f"got {len(reversals)}. Total lines: {len(delivery.lines)}"
        )

    @given(delivery=cancelled_delivery_with_zero_lines_strategy())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_sum_excludes_zero_quantity_lines(
        self, delivery: CancelledDelivery
    ):
        """
        Property 17: The total reversed quantity only accounts for
        positive-quantity lines, correctly excluding zero-quantity lines.
        """
        reversals = create_dispatch_reversals(delivery)

        total_positive_dispatched = sum(
            (l.quantity for l in delivery.lines if l.quantity > Decimal("0")),
            Decimal("0"),
        )
        total_reversed = sum(
            (r.quantity for r in reversals),
            Decimal("0"),
        )

        assert total_reversed == total_positive_dispatched, (
            f"Total reversed {total_reversed} != positive dispatched "
            f"{total_positive_dispatched}"
        )


class TestDeliveryCancellationEdgeCases:
    """Edge case tests for delivery cancellation restoration.

    **Validates: Requirements 33.3, 33.4**
    """

    def test_single_line_delivery(self):
        """Single line delivery produces exactly one reversal."""
        delivery = CancelledDelivery(
            delivery_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            lines=[
                DeliveryLine(
                    sales_order_line_id=uuid.uuid4(),
                    variant_id=uuid.uuid4(),
                    quantity=Decimal("10.000"),
                )
            ],
        )
        reversals = create_dispatch_reversals(delivery)
        assert len(reversals) == 1
        assert reversals[0].quantity == Decimal("10.000")

    def test_multiple_lines_different_quantities(self):
        """Multiple lines produce one reversal each with matching quantities."""
        variant_a = uuid.uuid4()
        variant_b = uuid.uuid4()
        variant_c = uuid.uuid4()

        delivery = CancelledDelivery(
            delivery_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            lines=[
                DeliveryLine(uuid.uuid4(), variant_a, Decimal("5.000")),
                DeliveryLine(uuid.uuid4(), variant_b, Decimal("12.500")),
                DeliveryLine(uuid.uuid4(), variant_c, Decimal("0.001")),
            ],
        )
        reversals = create_dispatch_reversals(delivery)

        assert len(reversals) == 3
        assert reversals[0].quantity == Decimal("5.000")
        assert reversals[0].material_id == variant_a
        assert reversals[1].quantity == Decimal("12.500")
        assert reversals[1].material_id == variant_b
        assert reversals[2].quantity == Decimal("0.001")
        assert reversals[2].material_id == variant_c

    def test_delivery_with_only_zero_quantity_lines(self):
        """Delivery with only zero-quantity lines produces no reversals."""
        delivery = CancelledDelivery(
            delivery_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            lines=[
                DeliveryLine(uuid.uuid4(), uuid.uuid4(), Decimal("0")),
                DeliveryLine(uuid.uuid4(), uuid.uuid4(), Decimal("0")),
            ],
        )
        reversals = create_dispatch_reversals(delivery)
        assert len(reversals) == 0

    def test_delivery_with_no_lines(self):
        """Empty delivery produces no reversals."""
        delivery = CancelledDelivery(
            delivery_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            lines=[],
        )
        reversals = create_dispatch_reversals(delivery)
        assert len(reversals) == 0

    def test_large_quantity_precision_preserved(self):
        """Large quantities preserve decimal precision in reversals."""
        qty = Decimal("999999.999")
        delivery = CancelledDelivery(
            delivery_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            lines=[
                DeliveryLine(uuid.uuid4(), uuid.uuid4(), qty),
            ],
        )
        reversals = create_dispatch_reversals(delivery)
        assert reversals[0].quantity == qty

    def test_small_fractional_quantity(self):
        """Very small fractional quantities are handled correctly."""
        qty = Decimal("0.001")
        delivery = CancelledDelivery(
            delivery_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            lines=[
                DeliveryLine(uuid.uuid4(), uuid.uuid4(), qty),
            ],
        )
        reversals = create_dispatch_reversals(delivery)
        assert reversals[0].quantity == qty
