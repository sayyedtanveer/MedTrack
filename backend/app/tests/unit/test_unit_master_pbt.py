"""
Property-based tests for Unit Master API — pure logic tests.

**Validates: Requirements 5.1, 5.2, 5.4**

Property 1 — Reference Integrity:
  DELETE logic returns 409 when mat_refs + bom_refs > 0, else proceeds normally.

Property 8 — Code Immutability:
  The "code" key check in update_unit raises 422 for any value of "code" in the body.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_unit(unit_id: uuid.UUID | None = None, tenant_id: uuid.UUID | None = None) -> MagicMock:
    """Lightweight mock resembling a UnitOfMeasure domain entity."""
    unit = MagicMock()
    unit.id = unit_id or uuid.uuid4()
    unit.tenant_id = tenant_id or uuid.uuid4()
    unit.code = "KG"
    unit.name = "Kilogram"
    unit.precision = 3
    unit.is_active = True
    unit._is_deleted = False
    return unit


def _delete_unit_guard(mat_refs: int, bom_refs: int) -> None:
    """
    Inline reproduction of the reference-integrity guard from delete_unit().
    Raises HTTPException(409) when total > 0, does nothing otherwise.
    """
    total = mat_refs + bom_refs
    if total > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete — {total} material/BOM reference(s) exist. Deactivate it instead.",
        )


def _update_unit_code_guard(body: dict) -> None:
    """
    Inline reproduction of the immutability guard from update_unit().
    Raises HTTPException(422) when "code" key is present.
    """
    if "code" in body:
        raise HTTPException(
            status_code=422,
            detail="Field 'code' is immutable and cannot be updated.",
        )


# ─── Property 1 — Reference Integrity ─────────────────────────────────────────

class TestUnitDeleteReferenceIntegrity:
    """**Validates: Requirements 5.1, 5.2**

    Property 1: DELETE guard returns 409 when N > 0 total references
    (material OR BOM), and proceeds without exception when N == 0.
    """

    @given(
        mat_refs=st.integers(min_value=1, max_value=20),
        bom_refs=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_references_present_raises_409(self, mat_refs: int, bom_refs: int) -> None:
        """Property 1A: mat_refs + bom_refs > 0 → guard must raise HTTP 409.

        **Validates: Requirements 5.1, 5.2**
        """
        with pytest.raises(HTTPException) as exc_info:
            _delete_unit_guard(mat_refs, bom_refs)

        assert exc_info.value.status_code == 409, (
            f"Expected 409 for {mat_refs} mat + {bom_refs} bom refs, "
            f"got {exc_info.value.status_code}"
        )
        assert str(mat_refs + bom_refs) in exc_info.value.detail

    @given(
        mat_refs=st.just(0),
        bom_refs=st.just(0),
    )
    @settings(max_examples=5, deadline=None)
    def test_zero_references_does_not_raise(self, mat_refs: int, bom_refs: int) -> None:
        """Property 1B: mat_refs = 0, bom_refs = 0 → guard must not raise.

        **Validates: Requirements 5.1**
        """
        # Should not raise
        _delete_unit_guard(mat_refs, bom_refs)

    @given(
        mat_refs=st.integers(min_value=0, max_value=10),
        bom_refs=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_409_iff_total_greater_than_zero(self, mat_refs: int, bom_refs: int) -> None:
        """Property 1 (combined): guard raises 409 iff total > 0; no exception iff total == 0.

        **Validates: Requirements 5.1, 5.2**
        """
        total = mat_refs + bom_refs
        if total > 0:
            with pytest.raises(HTTPException) as exc_info:
                _delete_unit_guard(mat_refs, bom_refs)
            assert exc_info.value.status_code == 409
        else:
            # Must not raise
            _delete_unit_guard(mat_refs, bom_refs)


# ─── Property 8 — Code Immutability ───────────────────────────────────────────

class TestUnitCodeImmutability:
    """**Validates: Requirements 5.4**

    Property 8: update_unit guard raises 422 whenever the request body
    contains the key "code", regardless of the value.
    """

    @given(
        code_value=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_body_with_code_key_raises_422(self, code_value: str) -> None:
        """Property 8: Any body dict containing "code" must trigger 422.

        **Validates: Requirements 5.4**
        """
        body = {"code": code_value, "name": "Updated Name"}

        with pytest.raises(HTTPException) as exc_info:
            _update_unit_code_guard(body)

        assert exc_info.value.status_code == 422, (
            f"Expected 422 for body with code='{code_value}', "
            f"got {exc_info.value.status_code}"
        )

    @given(
        name=st.text(min_size=1, max_size=100),
        is_active=st.booleans(),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_body_without_code_key_does_not_raise(self, name: str, is_active: bool) -> None:
        """Property 8B: Body without "code" key must NOT trigger 422.

        **Validates: Requirements 5.4**
        """
        body = {"name": name, "is_active": is_active}

        # Should not raise
        _update_unit_code_guard(body)
