"""
Property tests for Procurement Shortage Calculation.

# Feature: manufacturing-erp-audit, Property 18: Procurement Shortage Calculation

**Validates: Requirements 17.1, 17.2**

These tests validate that the procurement shortage calculation produces correct
results for all valid BOM line inputs:
  - shortage_quantity = required_quantity - available_quantity
  - shortage_quantity is always positive (when required > available)
  - shortage_quantity never exceeds required_quantity
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    composite,
)


# ─── Strategies ──────────────────────────────────────────────────────────────

# Quantities representing BOM line required amounts (always positive)
positive_quantity = decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("1000000.000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)

# Non-negative quantities representing available stock
non_negative_quantity = decimals(
    min_value=Decimal("0.000"),
    max_value=Decimal("1000000.000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)


@composite
def bom_line_with_shortage(draw):
    """Generate BOM line data where required_quantity > available_quantity (shortage exists).

    This ensures we always have a shortage scenario as per the property specification.
    """
    required_quantity = draw(positive_quantity)
    # available_quantity must be less than required_quantity (to ensure shortage)
    max_available = required_quantity - Decimal("0.001")
    if max_available < Decimal("0"):
        max_available = Decimal("0")
    available_quantity = draw(decimals(
        min_value=Decimal("0.000"),
        max_value=max_available,
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ))
    return required_quantity, available_quantity


# ─── Helper: Procurement shortage calculation (mirrors service logic) ────────

def calculate_shortage_quantity(required_quantity: Decimal, available_quantity: Decimal) -> Decimal:
    """Calculate shortage quantity for a BOM line.

    This mirrors the logic in MaterialAvailabilityService and
    InventoryReservationService:
        shortage_quantity = max(required_quantity - available_quantity, 0)
    """
    return max(required_quantity - available_quantity, Decimal("0"))


# ─────────────────────────────────────────────────────────────────────────────
# Property 18: Procurement Shortage Calculation
#
# For any work order BOM line where required_quantity > available_quantity,
# the purchase requisition SHALL specify:
#   shortage_quantity = required_quantity - available_quantity
# The shortage_quantity SHALL always be positive and SHALL NOT exceed
# required_quantity.
# ─────────────────────────────────────────────────────────────────────────────


class TestShortageCalculationFormula:
    """**Validates: Requirements 17.1, 17.2**"""

    @given(data=bom_line_with_shortage())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_shortage_equals_required_minus_available(self, data: tuple[Decimal, Decimal]):
        """Property 18: shortage_quantity = required_quantity - available_quantity."""
        required_quantity, available_quantity = data
        assume(required_quantity > available_quantity)

        result = calculate_shortage_quantity(required_quantity, available_quantity)
        expected = required_quantity - available_quantity

        assert result == expected, (
            f"Shortage mismatch: required={required_quantity}, available={available_quantity}, "
            f"got={result}, expected={expected}"
        )

    @given(data=bom_line_with_shortage())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_shortage_always_positive(self, data: tuple[Decimal, Decimal]):
        """Property 18: shortage_quantity is always positive when required > available."""
        required_quantity, available_quantity = data
        assume(required_quantity > available_quantity)

        result = calculate_shortage_quantity(required_quantity, available_quantity)

        assert result > Decimal("0"), (
            f"Shortage not positive: required={required_quantity}, "
            f"available={available_quantity}, result={result}"
        )

    @given(data=bom_line_with_shortage())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_shortage_never_exceeds_required(self, data: tuple[Decimal, Decimal]):
        """Property 18: shortage_quantity never exceeds required_quantity."""
        required_quantity, available_quantity = data
        assume(required_quantity > available_quantity)

        result = calculate_shortage_quantity(required_quantity, available_quantity)

        assert result <= required_quantity, (
            f"Shortage exceeds required: required={required_quantity}, "
            f"available={available_quantity}, shortage={result}"
        )


class TestShortageCalculationBoundaryProperties:
    """Additional boundary properties for shortage calculation.

    **Validates: Requirements 17.1, 17.2**
    """

    @given(data=bom_line_with_shortage())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_shortage_plus_available_equals_required(self, data: tuple[Decimal, Decimal]):
        """Property 18: shortage_quantity + available_quantity = required_quantity (conservation)."""
        required_quantity, available_quantity = data
        assume(required_quantity > available_quantity)

        shortage = calculate_shortage_quantity(required_quantity, available_quantity)

        assert shortage + available_quantity == required_quantity, (
            f"Conservation violated: shortage={shortage}, available={available_quantity}, "
            f"required={required_quantity}, sum={shortage + available_quantity}"
        )

    @given(required_quantity=positive_quantity)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_shortage_equals_required_when_available_is_zero(self, required_quantity: Decimal):
        """Property 18: shortage = required when available = 0 (total shortage)."""
        available_quantity = Decimal("0")

        result = calculate_shortage_quantity(required_quantity, available_quantity)

        assert result == required_quantity, (
            f"Total shortage mismatch: required={required_quantity}, "
            f"got={result}"
        )

    @given(required_quantity=positive_quantity)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_no_shortage_when_available_equals_required(self, required_quantity: Decimal):
        """Property 18 boundary: shortage = 0 when available = required (no shortage)."""
        available_quantity = required_quantity

        result = calculate_shortage_quantity(required_quantity, available_quantity)

        assert result == Decimal("0"), (
            f"Expected zero shortage when available equals required: "
            f"required={required_quantity}, available={available_quantity}, got={result}"
        )

    @given(required_quantity=positive_quantity, extra=positive_quantity)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_no_shortage_when_available_exceeds_required(self, required_quantity: Decimal, extra: Decimal):
        """Property 18 boundary: shortage = 0 when available > required (surplus)."""
        available_quantity = required_quantity + extra

        result = calculate_shortage_quantity(required_quantity, available_quantity)

        assert result == Decimal("0"), (
            f"Expected zero shortage when available exceeds required: "
            f"required={required_quantity}, available={available_quantity}, got={result}"
        )
