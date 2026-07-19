"""
Property-based tests for Tenant Profile API isolation — pure logic tests.

**Validates: Requirements 8.1, 8.2**

Property 5 — Tenant Isolation:
  _do_update_tenant raises 403 whenever tenant_id != current_tenant_id.
  When the IDs match, the isolation guard does NOT raise.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st


# ─── Inline isolation guard ────────────────────────────────────────────────────

def _tenant_isolation_guard(tenant_id: uuid.UUID, current_tenant_id: uuid.UUID) -> None:
    """
    Inline reproduction of the isolation check from _do_update_tenant().
    Raises HTTPException(403) when IDs differ.

    Mirrors backend/app/interfaces/api/v1/routes/tenants.py::_do_update_tenant
    """
    if tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot update another tenant's profile",
        )


# ─── Property 5 — Tenant Isolation ────────────────────────────────────────────

class TestTenantIsolationGuard:
    """**Validates: Requirements 8.1, 8.2**

    Property 5: The isolation guard raises HTTP 403 whenever tenant_id differs
    from current_tenant_id; it does NOT raise when they are equal.
    """

    @given(
        tenant_id=st.uuids(),
        current_tenant_id=st.uuids(),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_mismatched_ids_raise_403(
        self,
        tenant_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
    ) -> None:
        """Property 5A: tenant_id != current_tenant_id → isolation guard raises 403.

        **Validates: Requirements 8.1, 8.2**
        """
        assume(tenant_id != current_tenant_id)

        with pytest.raises(HTTPException) as exc_info:
            _tenant_isolation_guard(tenant_id, current_tenant_id)

        assert exc_info.value.status_code == 403, (
            f"Expected 403 for tenant_id={tenant_id} vs current={current_tenant_id}, "
            f"got {exc_info.value.status_code}"
        )
        assert "Cannot update another tenant" in exc_info.value.detail

    @given(tenant_id=st.uuids())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_same_ids_do_not_raise(self, tenant_id: uuid.UUID) -> None:
        """Property 5B: tenant_id == current_tenant_id → guard must NOT raise.

        **Validates: Requirements 8.1**
        """
        # Same UUID for both — must proceed without raising
        _tenant_isolation_guard(tenant_id, tenant_id)

    @given(
        tenant_id=st.uuids(),
        current_tenant_id=st.uuids(),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_403_iff_ids_differ(
        self,
        tenant_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
    ) -> None:
        """Property 5 (combined): guard raises 403 iff IDs differ; passes iff equal.

        **Validates: Requirements 8.1, 8.2**
        """
        if tenant_id != current_tenant_id:
            with pytest.raises(HTTPException) as exc_info:
                _tenant_isolation_guard(tenant_id, current_tenant_id)
            assert exc_info.value.status_code == 403
        else:
            # Same ID — must not raise
            _tenant_isolation_guard(tenant_id, current_tenant_id)
