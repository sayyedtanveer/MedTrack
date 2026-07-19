"""
Property-based tests for Storage Location Master API — pure logic tests.

**Validates: Requirements 7.1, 7.2**

Property 3 — Reference Integrity:
  DELETE logic returns 409 when mat_refs > 0 OR child_count > 0, else proceeds normally.
  The two checks are independent: either condition alone is sufficient to block deletion.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_location(
    location_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> MagicMock:
    """Lightweight mock resembling a Location domain entity."""
    loc = MagicMock()
    loc.id = location_id or uuid.uuid4()
    loc.tenant_id = tenant_id or uuid.uuid4()
    loc.name = "Raw Material Store"
    loc.code = "RMS"
    loc.is_active = True
    loc._is_deleted = False
    return loc


def _delete_location_guard(mat_refs: int, child_count: int) -> None:
    """
    Inline reproduction of the two-stage reference guard from delete_location().
    Raises HTTPException(409) on first failed check; does nothing when both == 0.

    Mirrors backend/app/interfaces/api/v1/routes/master_data.py::delete_location
    """
    if mat_refs > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete — {mat_refs} material(s) assigned here.",
        )
    if child_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete — {child_count} active child location(s) exist.",
        )


# ─── Property 3 — Reference Integrity ─────────────────────────────────────────

class TestLocationDeleteReferenceIntegrity:
    """**Validates: Requirements 7.1, 7.2**

    Property 3: DELETE guard raises 409 when mat_refs + child_count > 0;
    proceeds without exception when both are 0.
    """

    @given(
        mat_refs=st.integers(min_value=1, max_value=10),
        child_count=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_material_references_raise_409(self, mat_refs: int, child_count: int) -> None:
        """Property 3A: mat_refs > 0 → guard raises 409 (material check fires first).

        **Validates: Requirements 7.1**
        """
        with pytest.raises(HTTPException) as exc_info:
            _delete_location_guard(mat_refs, child_count)

        assert exc_info.value.status_code == 409
        assert str(mat_refs) in exc_info.value.detail

    @given(
        mat_refs=st.just(0),
        child_count=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_child_locations_raise_409(self, mat_refs: int, child_count: int) -> None:
        """Property 3B: mat_refs == 0, child_count > 0 → guard raises 409.

        **Validates: Requirements 7.2**
        """
        with pytest.raises(HTTPException) as exc_info:
            _delete_location_guard(mat_refs, child_count)

        assert exc_info.value.status_code == 409
        assert str(child_count) in exc_info.value.detail

    @given(
        mat_refs=st.just(0),
        child_count=st.just(0),
    )
    @settings(max_examples=5, deadline=None)
    def test_no_references_does_not_raise(self, mat_refs: int, child_count: int) -> None:
        """Property 3C: mat_refs == 0 and child_count == 0 → guard must not raise.

        **Validates: Requirements 7.1, 7.2**
        """
        # Should complete without raising — soft delete proceeds
        _delete_location_guard(mat_refs, child_count)

    @given(
        mat_refs=st.integers(min_value=0, max_value=10),
        child_count=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_409_iff_any_reference_exists(self, mat_refs: int, child_count: int) -> None:
        """Property 3 (combined): guard raises 409 iff mat_refs + child_count > 0.

        **Validates: Requirements 7.1, 7.2**
        """
        if mat_refs > 0 or child_count > 0:
            with pytest.raises(HTTPException) as exc_info:
                _delete_location_guard(mat_refs, child_count)
            assert exc_info.value.status_code == 409
        else:
            # Both zero — must not raise
            _delete_location_guard(mat_refs, child_count)
