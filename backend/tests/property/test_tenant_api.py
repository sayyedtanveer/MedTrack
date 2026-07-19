"""
Property-based tests for Tenant API — Tenant Isolation.

**Validates: Requirements 8.1, 8.2**

Property 5 — Tenant Isolation:
  For any two distinct tenant IDs (path_tenant_id ≠ jwt_tenant_id),
  PUT /tenants/{path_tenant_id} returns HTTP 403 Forbidden.
  Only when path_tenant_id == jwt_tenant_id does the update proceed.

# Feature: master-data-audit, Property 5: Tenant Isolation
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from backend.app.config import settings as app_settings
from backend.app.infrastructure.security.jwt_handler import JWTHandler

# ─── JWT helper ──────────────────────────────────────────────────────────────

_jwt = JWTHandler(
    secret_key=app_settings.jwt_secret_key,
    algorithm=app_settings.jwt_algorithm,
    expiry_minutes=app_settings.jwt_expiry_minutes,
)


def _headers_for_tenant(jwt_tenant_id: uuid.UUID) -> dict[str, str]:
    """Generate admin-role JWT headers whose tenant claim is jwt_tenant_id."""
    token = _jwt.create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(jwt_tenant_id),
        role="admin",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(jwt_tenant_id)}


# ─── Mock builders ────────────────────────────────────────────────────────────

def _make_tenant_model(tenant_id: uuid.UUID):
    """Return a lightweight mock that looks like a TenantModel ORM row."""
    tenant = MagicMock()
    tenant.id = tenant_id
    tenant.name = "Test Tenant"
    tenant.slug = f"test-{str(tenant_id)[:8]}"
    tenant.plan = "standard"
    tenant.is_active = True
    # Optional profile fields
    tenant.company_name = None
    tenant.gst_number = None
    tenant.address = None
    tenant.phone = None
    tenant.email = None
    tenant.logo_url = None
    tenant.footer_text = None
    tenant.currency_code = None
    tenant.currency_symbol = None
    tenant.timezone = None
    tenant.default_warehouse_name = None
    return tenant


# ─────────────────────────────────────────────────────────────────────────────
# Property 5: Tenant Isolation — cross-tenant PUT returns 403
# ─────────────────────────────────────────────────────────────────────────────


class TestTenantIsolation:
    """**Validates: Requirements 8.1, 8.2**

    Property 5: PUT /tenants/{tenant_id} returns 403 when tenant_id in the
    URL path does not match the tenant_id embedded in the caller's JWT.
    """

    @given(
        path_tenant_id=st.uuids(),
        jwt_tenant_id=st.uuids(),
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_cross_tenant_put_returns_403(
        self,
        path_tenant_id: uuid.UUID,
        jwt_tenant_id: uuid.UUID,
        async_client,
    ):
        """Property 5A: PUT /tenants/{id} returns 403 when path id ≠ JWT tenant.

        For ANY pair of distinct UUIDs (path ≠ jwt), the endpoint must refuse
        the update with 403 Forbidden — never 200, 422, or any success code.

        **Validates: Requirements 8.1, 8.2**
        """
        # Only test the cross-tenant scenario (the interesting property)
        assume(path_tenant_id != jwt_tenant_id)

        headers = _headers_for_tenant(jwt_tenant_id)

        # The isolation check happens before any repository call,
        # but we still patch to ensure no side effects occur.
        with (
            patch(
                "backend.app.interfaces.api.v1.routes.tenants.TenantRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.update = AsyncMock(return_value=None)

            response = await async_client.put(
                f"/api/v1/tenants/{path_tenant_id}",
                json={"company_name": "Attacker Corp"},
                headers=headers,
            )

        assert response.status_code == 403, (
            f"Expected 403 Forbidden for cross-tenant PUT "
            f"(path={path_tenant_id}, jwt={jwt_tenant_id}), "
            f"got {response.status_code}. Body: {response.text}"
        )

        # Also confirm the repository was never called (no data leak / mutation)
        repo_instance.update.assert_not_called()

    @given(
        tenant_id=st.uuids(),
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_same_tenant_put_does_not_return_403(
        self,
        tenant_id: uuid.UUID,
        async_client,
    ):
        """Property 5B: PUT /tenants/{id} does NOT return 403 when path id == JWT tenant.

        **Validates: Requirements 8.1**
        """
        # Same tenant in path and JWT
        headers = _headers_for_tenant(tenant_id)
        tenant_mock = _make_tenant_model(tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.tenants.TenantRepository"
            ) as MockRepo,
            patch(
                "backend.app.interfaces.api.v1.routes.tenants._fetch_tenant_model",
                new_callable=AsyncMock,
            ) as mock_fetch,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.update = AsyncMock(return_value=None)
            mock_fetch.return_value = tenant_mock

            response = await async_client.put(
                f"/api/v1/tenants/{tenant_id}",
                json={"company_name": "Legitimate Update"},
                headers=headers,
            )

        # Must NOT be a 403 isolation error (may be 200 on success or 422 for
        # field validation — but NOT 403 for isolation)
        assert response.status_code != 403, (
            f"Same-tenant PUT should not be rejected with 403, "
            f"got {response.status_code}. Body: {response.text}"
        )

    @given(
        path_tenant_id=st.uuids(),
        jwt_tenant_id=st.uuids(),
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_cross_tenant_403_detail_mentions_tenant(
        self,
        path_tenant_id: uuid.UUID,
        jwt_tenant_id: uuid.UUID,
        async_client,
    ):
        """Property 5C: The 403 response body contains an informative detail message.

        **Validates: Requirements 8.2**
        """
        assume(path_tenant_id != jwt_tenant_id)

        headers = _headers_for_tenant(jwt_tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.tenants.TenantRepository"
            ),
        ):
            response = await async_client.put(
                f"/api/v1/tenants/{path_tenant_id}",
                json={"company_name": "Probe"},
                headers=headers,
            )

        assert response.status_code == 403

        body_lower = response.text.lower()
        # The response should mention the access denial — not a generic 403
        assert any(
            keyword in body_lower
            for keyword in ("tenant", "cannot", "forbidden", "access", "denied", "update")
        ), (
            f"403 response body should contain an informative message about tenant isolation. "
            f"Got: {response.text}"
        )
