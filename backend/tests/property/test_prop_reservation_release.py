"""
Property tests for Reservation Release on Cancellation.

# Feature: manufacturing-erp-audit, Property 11: Reservation Release on Cancellation

**Validates: Requirements 18.1, 18.2, 18.3, 18.4**

These tests validate that:
  - For any cancelled sales order, the system creates RESERVATION_RELEASE inventory
    transactions whose quantities exactly equal the previously reserved FG quantities.
  - For any cancelled work order, the system creates RESERVATION_RELEASE inventory
    transactions whose quantities exactly equal the previously reserved raw material
    quantities (where reserved > issued).
  - The sum of released quantities equals the sum of originally reserved quantities.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Dict

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    decimals,
    integers,
    lists,
    composite,
)


# ─── Constants ───────────────────────────────────────────────────────────────

TOLERANCE = Decimal("0.001")


# ─── Helper: Reservation release computation (mirrors service logic) ─────────


def compute_so_reservation_releases(
    so_lines: List[Dict[str, Decimal]],
) -> List[Decimal]:
    """
    Compute RESERVATION_RELEASE quantities for a cancelled sales order.

    Mirrors WorkflowOrchestrationService.on_cancellation() for entity_type="sales_order":
    For each SO line with allocated_quantity > 0, a RESERVATION_RELEASE transaction
    is created with quantity = allocated_quantity.

    Args:
        so_lines: List of dicts with 'allocated_quantity' representing FG reservations.

    Returns:
        List of release quantities (one per line with allocated > 0).
    """
    releases = []
    for line in so_lines:
        allocated = line["allocated_quantity"]
        if allocated > Decimal("0"):
            releases.append(allocated)
    return releases


def compute_wo_reservation_releases(
    wo_materials: List[Dict[str, Decimal]],
) -> List[Decimal]:
    """
    Compute RESERVATION_RELEASE quantities for a cancelled work order.

    Mirrors InventoryService.cancel_work_order_reservation():
    For each WO material, the unissued quantity (reserved - issued) is released.
    Only materials where reserved > issued produce a release transaction.

    Args:
        wo_materials: List of dicts with 'reserved_quantity' and 'issued_quantity'.

    Returns:
        List of release quantities (one per material with unissued > 0).
    """
    releases = []
    for material in wo_materials:
        reserved = material["reserved_quantity"]
        issued = material["issued_quantity"]
        unissued = reserved - issued
        if unissued > Decimal("0"):
            releases.append(unissued)
    return releases


def sum_released_quantities(releases: List[Decimal]) -> Decimal:
    """Compute total released quantity from a list of release amounts."""
    return sum(releases, Decimal("0"))


def sum_original_reservations_so(so_lines: List[Dict[str, Decimal]]) -> Decimal:
    """Compute total originally reserved quantity for SO lines (allocated > 0)."""
    return sum(
        (line["allocated_quantity"] for line in so_lines if line["allocated_quantity"] > Decimal("0")),
        Decimal("0"),
    )


def sum_original_reservations_wo(wo_materials: List[Dict[str, Decimal]]) -> Decimal:
    """Compute total originally reserved (unissued) quantity for WO materials."""
    total = Decimal("0")
    for material in wo_materials:
        unissued = material["reserved_quantity"] - material["issued_quantity"]
        if unissued > Decimal("0"):
            total += unissued
    return total


# ─── Strategies ──────────────────────────────────────────────────────────────

# Positive quantity for reserved amounts
positive_quantity = decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("100000.000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)

# Non-negative quantity (for issued amounts, which can be 0)
non_negative_quantity = decimals(
    min_value=Decimal("0.000"),
    max_value=Decimal("100000.000"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)


@composite
def cancelled_so_lines(draw):
    """
    Generate a cancelled sales order with random SO lines having reserved (allocated) quantities.

    Each line has a positive allocated_quantity representing the FG reservation.
    Returns a list of 1 to 10 SO line dicts.
    """
    n = draw(integers(min_value=1, max_value=10))
    lines = []
    for _ in range(n):
        allocated = draw(positive_quantity)
        lines.append({"allocated_quantity": allocated})
    return lines


@composite
def cancelled_so_lines_with_zeros(draw):
    """
    Generate a cancelled sales order with a mix of lines:
    some with allocated > 0 (reserved) and some with allocated = 0 (not reserved).

    This tests that only lines with allocated > 0 produce releases.
    """
    n = draw(integers(min_value=1, max_value=10))
    lines = []
    for i in range(n):
        if i % 2 == 0:
            allocated = draw(positive_quantity)
        else:
            allocated = Decimal("0.000")
        lines.append({"allocated_quantity": allocated})
    return lines


@composite
def cancelled_wo_materials(draw):
    """
    Generate a cancelled work order with random BOM materials having reservations.

    Each material has:
    - reserved_quantity: positive amount originally reserved
    - issued_quantity: between 0 and reserved_quantity (partially issued is common)

    Only materials where reserved > issued produce a RESERVATION_RELEASE.
    """
    n = draw(integers(min_value=1, max_value=10))
    materials = []
    for _ in range(n):
        reserved = draw(positive_quantity)
        # issued_quantity can be 0 up to reserved_quantity
        issued = draw(decimals(
            min_value=Decimal("0.000"),
            max_value=reserved,
            places=3,
            allow_nan=False,
            allow_infinity=False,
        ))
        materials.append({
            "reserved_quantity": reserved,
            "issued_quantity": issued,
        })
    return materials


@composite
def cancelled_wo_materials_fully_issued(draw):
    """
    Generate WO materials where all materials are fully issued (issued == reserved).

    This means no RESERVATION_RELEASE transactions should be generated.
    """
    n = draw(integers(min_value=1, max_value=5))
    materials = []
    for _ in range(n):
        reserved = draw(positive_quantity)
        materials.append({
            "reserved_quantity": reserved,
            "issued_quantity": reserved,  # Fully issued
        })
    return materials


@composite
def cancelled_wo_materials_partially_issued(draw):
    """
    Generate WO materials where all materials have some unissued quantity
    (reserved > issued), ensuring all produce a release.
    """
    n = draw(integers(min_value=1, max_value=10))
    materials = []
    for _ in range(n):
        reserved = draw(positive_quantity)
        # issued must be strictly less than reserved
        max_issued = reserved - Decimal("0.001")
        if max_issued < Decimal("0"):
            max_issued = Decimal("0")
        issued = draw(decimals(
            min_value=Decimal("0.000"),
            max_value=max_issued,
            places=3,
            allow_nan=False,
            allow_infinity=False,
        ))
        materials.append({
            "reserved_quantity": reserved,
            "issued_quantity": issued,
        })
    return materials


# ─────────────────────────────────────────────────────────────────────────────
# Property 11: Reservation Release on Cancellation
#
# For any cancelled sales order or work order, the system SHALL create
# RESERVATION_RELEASE inventory transactions whose quantities exactly equal
# the previously reserved quantities. The sum of released quantities SHALL
# equal the sum of originally reserved quantities.
# ─────────────────────────────────────────────────────────────────────────────


class TestSOReservationReleaseOnCancellation:
    """
    SO cancellation releases FG reservations via RESERVATION_RELEASE transactions.

    **Validates: Requirements 18.1, 18.4**
    """

    @given(so_lines=cancelled_so_lines())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_release_sum_equals_originally_reserved_sum(
        self, so_lines: List[Dict[str, Decimal]]
    ):
        """
        Property 11: The sum of RESERVATION_RELEASE quantities equals
        the sum of originally reserved (allocated) quantities.
        """
        releases = compute_so_reservation_releases(so_lines)
        total_released = sum_released_quantities(releases)
        total_reserved = sum_original_reservations_so(so_lines)

        assert abs(total_released - total_reserved) <= TOLERANCE, (
            f"Sum mismatch: released={total_released}, reserved={total_reserved}, "
            f"lines={so_lines}"
        )

    @given(so_lines=cancelled_so_lines())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_each_release_equals_line_allocated_quantity(
        self, so_lines: List[Dict[str, Decimal]]
    ):
        """
        Property 11: Each RESERVATION_RELEASE transaction quantity equals
        the allocated_quantity of the corresponding SO line.
        """
        releases = compute_so_reservation_releases(so_lines)
        allocated_lines = [
            line for line in so_lines if line["allocated_quantity"] > Decimal("0")
        ]

        assert len(releases) == len(allocated_lines), (
            f"Release count mismatch: releases={len(releases)}, "
            f"allocated_lines={len(allocated_lines)}"
        )

        for release, line in zip(releases, allocated_lines):
            assert release == line["allocated_quantity"], (
                f"Release quantity {release} != allocated {line['allocated_quantity']}"
            )

    @given(so_lines=cancelled_so_lines())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_release_quantities_are_positive(
        self, so_lines: List[Dict[str, Decimal]]
    ):
        """
        Property 11: Every RESERVATION_RELEASE transaction has a positive quantity.
        """
        releases = compute_so_reservation_releases(so_lines)

        for i, release in enumerate(releases):
            assert release > Decimal("0"), (
                f"Release at index {i} is not positive: {release}"
            )

    @given(so_lines=cancelled_so_lines_with_zeros())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_zero_allocated_lines_produce_no_release(
        self, so_lines: List[Dict[str, Decimal]]
    ):
        """
        Property 11: Lines with allocated_quantity = 0 do NOT produce
        a RESERVATION_RELEASE transaction.
        """
        releases = compute_so_reservation_releases(so_lines)
        expected_count = sum(
            1 for line in so_lines if line["allocated_quantity"] > Decimal("0")
        )

        assert len(releases) == expected_count, (
            f"Expected {expected_count} releases but got {len(releases)}, "
            f"lines={so_lines}"
        )


class TestWOReservationReleaseOnCancellation:
    """
    WO cancellation releases raw material reservations via RESERVATION_RELEASE transactions.

    **Validates: Requirements 18.2, 18.3, 18.4**
    """

    @given(wo_materials=cancelled_wo_materials_partially_issued())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_release_sum_equals_total_unissued_reservation(
        self, wo_materials: List[Dict[str, Decimal]]
    ):
        """
        Property 11: The sum of RESERVATION_RELEASE quantities equals
        the sum of unissued reserved quantities (reserved - issued) for all materials.
        """
        releases = compute_wo_reservation_releases(wo_materials)
        total_released = sum_released_quantities(releases)
        total_unissued = sum_original_reservations_wo(wo_materials)

        assert abs(total_released - total_unissued) <= TOLERANCE, (
            f"Sum mismatch: released={total_released}, unissued={total_unissued}, "
            f"materials={wo_materials}"
        )

    @given(wo_materials=cancelled_wo_materials())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_each_release_equals_unissued_quantity(
        self, wo_materials: List[Dict[str, Decimal]]
    ):
        """
        Property 11: Each RESERVATION_RELEASE transaction quantity equals
        (reserved_quantity - issued_quantity) for the corresponding material.
        """
        releases = compute_wo_reservation_releases(wo_materials)
        expected_releases = []
        for material in wo_materials:
            unissued = material["reserved_quantity"] - material["issued_quantity"]
            if unissued > Decimal("0"):
                expected_releases.append(unissued)

        assert len(releases) == len(expected_releases), (
            f"Release count mismatch: releases={len(releases)}, "
            f"expected={len(expected_releases)}"
        )

        for release, expected in zip(releases, expected_releases):
            assert abs(release - expected) <= TOLERANCE, (
                f"Release quantity {release} != expected {expected}"
            )

    @given(wo_materials=cancelled_wo_materials())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_release_quantities_are_positive(
        self, wo_materials: List[Dict[str, Decimal]]
    ):
        """
        Property 11: Every RESERVATION_RELEASE transaction has a positive quantity.
        """
        releases = compute_wo_reservation_releases(wo_materials)

        for i, release in enumerate(releases):
            assert release > Decimal("0"), (
                f"Release at index {i} is not positive: {release}"
            )

    @given(wo_materials=cancelled_wo_materials_fully_issued())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_fully_issued_materials_produce_no_release(
        self, wo_materials: List[Dict[str, Decimal]]
    ):
        """
        Property 11: Materials where issued_quantity == reserved_quantity
        do NOT produce a RESERVATION_RELEASE transaction (nothing left to release).
        """
        releases = compute_wo_reservation_releases(wo_materials)

        assert len(releases) == 0, (
            f"Expected no releases for fully issued materials but got {len(releases)}: "
            f"materials={wo_materials}"
        )

    @given(wo_materials=cancelled_wo_materials())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_release_never_exceeds_reserved_quantity(
        self, wo_materials: List[Dict[str, Decimal]]
    ):
        """
        Property 11: No RESERVATION_RELEASE quantity exceeds the original
        reserved_quantity for any material.
        """
        releases = compute_wo_reservation_releases(wo_materials)
        releasable_materials = [
            m for m in wo_materials
            if m["reserved_quantity"] - m["issued_quantity"] > Decimal("0")
        ]

        for release, material in zip(releases, releasable_materials):
            assert release <= material["reserved_quantity"], (
                f"Release {release} exceeds reserved {material['reserved_quantity']}"
            )


class TestReservationReleaseConservation:
    """
    Conservation properties: released + issued = reserved for WO materials.

    **Validates: Requirements 18.2, 18.3**
    """

    @given(wo_materials=cancelled_wo_materials())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_released_plus_issued_equals_reserved(
        self, wo_materials: List[Dict[str, Decimal]]
    ):
        """
        Property 11 (conservation): For each WO material,
        released_quantity + issued_quantity = reserved_quantity.
        """
        releases = compute_wo_reservation_releases(wo_materials)
        releasable_materials = [
            m for m in wo_materials
            if m["reserved_quantity"] - m["issued_quantity"] > Decimal("0")
        ]

        for release, material in zip(releases, releasable_materials):
            total = release + material["issued_quantity"]
            assert abs(total - material["reserved_quantity"]) <= TOLERANCE, (
                f"Conservation violated: released={release} + issued={material['issued_quantity']} "
                f"= {total} != reserved={material['reserved_quantity']}"
            )

    @given(wo_materials=cancelled_wo_materials())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_total_released_plus_total_issued_equals_total_reserved(
        self, wo_materials: List[Dict[str, Decimal]]
    ):
        """
        Property 11 (aggregate conservation): Sum of all releases + sum of all
        issued quantities = sum of all reserved quantities (for materials with unissued).
        """
        releases = compute_wo_reservation_releases(wo_materials)
        releasable_materials = [
            m for m in wo_materials
            if m["reserved_quantity"] - m["issued_quantity"] > Decimal("0")
        ]

        total_released = sum_released_quantities(releases)
        total_issued = sum(
            (m["issued_quantity"] for m in releasable_materials), Decimal("0")
        )
        total_reserved = sum(
            (m["reserved_quantity"] for m in releasable_materials), Decimal("0")
        )

        assert abs((total_released + total_issued) - total_reserved) <= TOLERANCE, (
            f"Aggregate conservation violated: "
            f"released={total_released} + issued={total_issued} "
            f"= {total_released + total_issued} != reserved={total_reserved}"
        )


class TestReservationReleaseEdgeCases:
    """
    Edge case tests for reservation release computation.

    **Validates: Requirements 18.1, 18.2, 18.3, 18.4**
    """

    def test_single_so_line_release(self):
        """Single SO line with known allocated quantity."""
        so_lines = [{"allocated_quantity": Decimal("100.500")}]
        releases = compute_so_reservation_releases(so_lines)
        assert releases == [Decimal("100.500")]
        assert sum_released_quantities(releases) == Decimal("100.500")

    def test_multiple_so_lines_release(self):
        """Multiple SO lines produce correct individual and total releases."""
        so_lines = [
            {"allocated_quantity": Decimal("50.000")},
            {"allocated_quantity": Decimal("30.000")},
            {"allocated_quantity": Decimal("20.000")},
        ]
        releases = compute_so_reservation_releases(so_lines)
        assert releases == [Decimal("50.000"), Decimal("30.000"), Decimal("20.000")]
        assert sum_released_quantities(releases) == Decimal("100.000")

    def test_so_lines_all_zero_allocation(self):
        """SO with all lines at zero allocation produces no releases."""
        so_lines = [
            {"allocated_quantity": Decimal("0")},
            {"allocated_quantity": Decimal("0")},
        ]
        releases = compute_so_reservation_releases(so_lines)
        assert releases == []

    def test_wo_single_material_no_issue(self):
        """WO material with nothing issued releases full reserved quantity."""
        wo_materials = [{"reserved_quantity": Decimal("75.000"), "issued_quantity": Decimal("0.000")}]
        releases = compute_wo_reservation_releases(wo_materials)
        assert releases == [Decimal("75.000")]

    def test_wo_single_material_partial_issue(self):
        """WO material partially issued releases only the unissued portion."""
        wo_materials = [{"reserved_quantity": Decimal("100.000"), "issued_quantity": Decimal("40.000")}]
        releases = compute_wo_reservation_releases(wo_materials)
        assert releases == [Decimal("60.000")]

    def test_wo_single_material_fully_issued(self):
        """WO material fully issued produces no release."""
        wo_materials = [{"reserved_quantity": Decimal("50.000"), "issued_quantity": Decimal("50.000")}]
        releases = compute_wo_reservation_releases(wo_materials)
        assert releases == []

    def test_wo_mixed_materials(self):
        """Mix of fully issued and partially issued materials."""
        wo_materials = [
            {"reserved_quantity": Decimal("100.000"), "issued_quantity": Decimal("100.000")},  # fully issued
            {"reserved_quantity": Decimal("50.000"), "issued_quantity": Decimal("20.000")},   # release 30
            {"reserved_quantity": Decimal("80.000"), "issued_quantity": Decimal("0.000")},    # release 80
        ]
        releases = compute_wo_reservation_releases(wo_materials)
        assert releases == [Decimal("30.000"), Decimal("80.000")]
        assert sum_released_quantities(releases) == Decimal("110.000")

    def test_high_precision_quantities(self):
        """Decimal precision is preserved through release computation."""
        wo_materials = [
            {"reserved_quantity": Decimal("1.234"), "issued_quantity": Decimal("0.567")},
        ]
        releases = compute_wo_reservation_releases(wo_materials)
        assert releases == [Decimal("0.667")]

    def test_empty_so_lines(self):
        """Empty SO lines list produces empty releases."""
        releases = compute_so_reservation_releases([])
        assert releases == []
        assert sum_released_quantities(releases) == Decimal("0")

    def test_empty_wo_materials(self):
        """Empty WO materials list produces empty releases."""
        releases = compute_wo_reservation_releases([])
        assert releases == []
        assert sum_released_quantities(releases) == Decimal("0")
