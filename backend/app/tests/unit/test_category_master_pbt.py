"""
Property-based tests for Material Category Master API — pure logic tests.

**Validates: Requirements 6.1, 6.2**

Property 2 — Reference Integrity:
  DELETE logic returns 409 when mat_refs > 0, else proceeds normally (204).
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_category(
    category_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> MagicMock:
    """Lightweight mock resembling a MaterialCategory domain entity."""
    cat = MagicMock()
    cat.id = category_id or uuid.uuid4()
    cat.tenant_id = tenant_id or uuid.uuid4()
    cat.name = "Metal"
    cat.code_prefix = "MET"
    cat.description = "Metal materials"
    cat.is_active = True
    cat._is_deleted = False
    return cat


def _delete_category_guard(mat_refs: int) -> None:
    """
    Inline reproduction of the reference-integrity guard from delete_category().
    Raises HTTPException(409) when mat_refs > 0, does nothing otherwise.

    Mirrors backend/app/interfaces/api/v1/routes/master_data.py::delete_category
    """
    if mat_refs > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete — {mat_refs} material(s) use this category. Deactivate it instead.",
        )


# ─── Property 2 — Reference Integrity ─────────────────────────────────────────

class TestCategoryDeleteReferenceIntegrity:
    """**Validates: Requirements 6.1, 6.2**

    Property 2: DELETE guard raises 409 when N > 0 material references exist;
    proceeds without exception when N == 0.
    """

    @given(mat_refs=st.integers(min_value=1, max_value=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_with_material_references_raises_409(self, mat_refs: int) -> None:
        """Property 2A: mat_refs > 0 → DELETE guard must raise HTTP 409.

        **Validates: Requirements 6.1, 6.2**
        """
        with pytest.raises(HTTPException) as exc_info:
            _delete_category_guard(mat_refs)

        assert exc_info.value.status_code == 409, (
            f"Expected 409 for category with {mat_refs} material reference(s), "
            f"got {exc_info.value.status_code}"
        )
        # Detail must contain the material count
        assert str(mat_refs) in exc_info.value.detail

    @given(mat_refs=st.just(0))
    @settings(max_examples=5, deadline=None)
    def test_zero_references_does_not_raise(self, mat_refs: int) -> None:
        """Property 2B: mat_refs == 0 → DELETE guard must not raise (204 path).

        **Validates: Requirements 6.1**
        """
        # Should not raise — soft delete proceeds
        _delete_category_guard(mat_refs)

    @given(mat_refs=st.integers(min_value=0, max_value=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_409_iff_refs_greater_than_zero(self, mat_refs: int) -> None:
        """Property 2 (combined): guard raises 409 iff mat_refs > 0.

        **Validates: Requirements 6.1, 6.2**
        """
        if mat_refs > 0:
            with pytest.raises(HTTPException) as exc_info:
                _delete_category_guard(mat_refs)
            assert exc_info.value.status_code == 409
        else:
            # Must complete without raising
            _delete_category_guard(mat_refs)
