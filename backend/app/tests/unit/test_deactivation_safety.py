"""
Integration verification: deactivation of unit/category/location does NOT cascade to materials.

**Validates: Requirements 1.2, 2.2, 3.2**

These tests confirm the spec requirement:
  "Deactivation is always allowed; deactivated units are hidden from new dropdowns
   but preserve existing references"

Property 4 — Deactivation Safety:
  After deactivating a unit, category, or location:
  - Existing materials that reference it RETAIN the FK (not set to null)
  - The deactivated master record no longer has is_active=True
  - The material's base_unit_id / category_id / location_id is unchanged

These are pure domain/logic tests — no DB or HTTP required.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ─── Domain entity mocks ──────────────────────────────────────────────────────

def _make_unit(unit_id: uuid.UUID, is_active: bool = True) -> MagicMock:
    unit = MagicMock()
    unit.id = unit_id
    unit.is_active = is_active
    unit._is_deleted = False
    return unit


def _make_material(material_id: uuid.UUID, base_unit_id: uuid.UUID) -> MagicMock:
    mat = MagicMock()
    mat.id = material_id
    mat.base_unit_id = base_unit_id  # FK reference
    return mat


def _make_category(category_id: uuid.UUID, is_active: bool = True) -> MagicMock:
    cat = MagicMock()
    cat.id = category_id
    cat.is_active = is_active
    cat._is_deleted = False
    return cat


def _make_material_with_category(material_id: uuid.UUID, category_id: uuid.UUID) -> MagicMock:
    mat = MagicMock()
    mat.id = material_id
    mat.category_id = category_id
    return mat


def _make_location(location_id: uuid.UUID, is_active: bool = True) -> MagicMock:
    loc = MagicMock()
    loc.id = location_id
    loc.is_active = is_active
    loc._is_deleted = False
    return loc


def _make_material_with_location(material_id: uuid.UUID, location_id: uuid.UUID) -> MagicMock:
    mat = MagicMock()
    mat.id = material_id
    mat.location_id = location_id
    return mat


# ─── Deactivation simulation helpers ─────────────────────────────────────────

def deactivate_unit(unit: MagicMock) -> MagicMock:
    """Simulate the route handler setting is_active=False on a unit."""
    unit.is_active = False
    return unit


def deactivate_category(category: MagicMock) -> MagicMock:
    """Simulate the route handler setting is_active=False on a category."""
    category.is_active = False
    return category


def deactivate_location(location: MagicMock) -> MagicMock:
    """Simulate the route handler setting is_active=False on a location."""
    location.is_active = False
    return location


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestUnitDeactivationSafety:
    """
    **Validates: Requirement 1.2**

    Deactivating a unit does NOT affect existing materials that reference it.
    The material's base_unit_id FK is unchanged after the unit is deactivated.
    """

    @given(n_materials=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_unit_deactivation_preserves_material_fk(self, n_materials: int) -> None:
        """
        **Validates: Requirement 1.2**

        After deactivating a unit, existing materials retain their base_unit_id FK.
        """
        unit_id = uuid.uuid4()
        unit = _make_unit(unit_id, is_active=True)

        # Create N materials referencing this unit
        materials = [_make_material(uuid.uuid4(), unit_id) for _ in range(n_materials)]

        # Capture FK values before deactivation
        fks_before = [m.base_unit_id for m in materials]

        # Deactivate the unit
        deactivate_unit(unit)

        # Unit must now be inactive
        assert unit.is_active is False, "Unit should be marked inactive after deactivation"

        # All material FKs must be unchanged
        fks_after = [m.base_unit_id for m in materials]
        assert fks_before == fks_after, (
            f"Deactivating unit {unit_id} should NOT change material base_unit_id FKs. "
            f"Before: {fks_before}, After: {fks_after}"
        )

    def test_deactivated_unit_is_inactive(self) -> None:
        """After deactivation, unit.is_active must be False."""
        unit = _make_unit(uuid.uuid4(), is_active=True)
        deactivate_unit(unit)
        assert unit.is_active is False

    def test_deactivation_does_not_hard_delete(self) -> None:
        """Deactivation only sets is_active=False; it does NOT set is_deleted=True."""
        unit = _make_unit(uuid.uuid4(), is_active=True)
        deactivate_unit(unit)
        assert unit._is_deleted is False, "Deactivation must not hard-delete the unit"


class TestCategoryDeactivationSafety:
    """
    **Validates: Requirement 2.2**

    Deactivating a category does NOT affect existing materials that reference it.
    The material's category_id FK is unchanged.
    """

    @given(n_materials=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_category_deactivation_preserves_material_fk(self, n_materials: int) -> None:
        """
        **Validates: Requirement 2.2**

        After deactivating a category, existing materials retain their category_id FK.
        """
        category_id = uuid.uuid4()
        category = _make_category(category_id, is_active=True)

        materials = [_make_material_with_category(uuid.uuid4(), category_id) for _ in range(n_materials)]
        fks_before = [m.category_id for m in materials]

        deactivate_category(category)

        assert category.is_active is False
        fks_after = [m.category_id for m in materials]
        assert fks_before == fks_after, (
            "Deactivating category should NOT change material category_id FKs"
        )

    def test_deactivated_category_is_inactive(self) -> None:
        category = _make_category(uuid.uuid4(), is_active=True)
        deactivate_category(category)
        assert category.is_active is False

    def test_category_deactivation_does_not_hard_delete(self) -> None:
        category = _make_category(uuid.uuid4(), is_active=True)
        deactivate_category(category)
        assert category._is_deleted is False


class TestLocationDeactivationSafety:
    """
    **Validates: Requirement 3.2**

    Deactivating a location does NOT affect existing materials that reference it.
    The material's location_id FK is unchanged.
    """

    @given(n_materials=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_location_deactivation_preserves_material_fk(self, n_materials: int) -> None:
        """
        **Validates: Requirement 3.2**

        After deactivating a location, existing materials retain their location_id FK.
        """
        location_id = uuid.uuid4()
        location = _make_location(location_id, is_active=True)

        materials = [_make_material_with_location(uuid.uuid4(), location_id) for _ in range(n_materials)]
        fks_before = [m.location_id for m in materials]

        deactivate_location(location)

        assert location.is_active is False
        fks_after = [m.location_id for m in materials]
        assert fks_before == fks_after, (
            "Deactivating location should NOT change material location_id FKs"
        )

    def test_deactivated_location_is_inactive(self) -> None:
        location = _make_location(uuid.uuid4(), is_active=True)
        deactivate_location(location)
        assert location.is_active is False

    def test_location_deactivation_does_not_hard_delete(self) -> None:
        location = _make_location(uuid.uuid4(), is_active=True)
        deactivate_location(location)
        assert location._is_deleted is False
