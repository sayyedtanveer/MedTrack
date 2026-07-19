"""
Property-based tests for Location Master API.

**Validates: Requirements 7.1, 7.2**

Property 3 — Location Reference Integrity:
  For any location with N > 0 material references OR M > 0 active child locations,
  DELETE returns HTTP 409.
  For N == 0 and M == 0, DELETE returns HTTP 204.

# Feature: master-data-audit, Property 3: Location Reference Integrity
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from backend.app.config import settings as app_settings
from backend.app.infrastructure.security.jwt_handler import JWTHandler

# ─── JWT helper ──────────────────────────────────────────────────────────────

_jwt = JWTHandler(
    secret_key=app_settings.jwt_secret_key,
    algorithm=app_settings.jwt_algorithm,
    expiry_minutes=app_settings.jwt_expiry_minutes,
)


def _admin_headers(tenant_id: uuid.UUID) -> dict[str, str]:
    """Generate admin-role JWT headers for a given tenant."""
    token = _jwt.create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        role="admin",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


# ─── Mock builders ────────────────────────────────────────────────────────────

def _make_location_entity(location_id: uuid.UUID, tenant_id: uuid.UUID) -> Any:
    """Return a lightweight mock that looks like a Location domain entity."""
    loc = MagicMock()
    loc.id = location_id
    loc.tenant_id = tenant_id
    loc.name = "Test Warehouse"
    loc.code = "WH-01"
    loc.location_type = MagicMock()
    loc.location_type.value = "warehouse"
    loc.parent_location_id = None
    loc.is_active = True
    loc._is_deleted = False
    return loc


# ─────────────────────────────────────────────────────────────────────────────
# Property 3: Reference Integrity — DELETE returns 409 when references exist
# ─────────────────────────────────────────────────────────────────────────────


class TestLocationDeleteReferenceIntegrity:
    """**Validates: Requirements 7.1, 7.2**

    Property 3: DELETE /locations/{id} returns 409 when the location has
    any material references OR active child locations.
    Returns 204 when both counts are zero.
    """

    @given(n=st.integers(min_value=1, max_value=10))
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_delete_with_material_references_returns_409(
        self,
        n: int,
        async_client,
    ):
        """Property 3A: DELETE a location with N > 0 material references returns 409.

        **Validates: Requirements 7.1**
        """
        tenant_id = uuid.uuid4()
        location_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        loc_mock = _make_location_entity(location_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.LocationRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=loc_mock)
            repo_instance.count_material_references = AsyncMock(return_value=n)
            repo_instance.count_active_children = AsyncMock(return_value=0)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/locations/{location_id}",
                headers=headers,
            )

        assert response.status_code == 409, (
            f"Expected 409 Conflict for location with {n} material reference(s), "
            f"got {response.status_code}. Body: {response.text}"
        )

    @given(m=st.integers(min_value=1, max_value=10))
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_delete_with_active_children_returns_409(
        self,
        m: int,
        async_client,
    ):
        """Property 3B: DELETE a location with M > 0 active child locations returns 409.

        **Validates: Requirements 7.2**
        """
        tenant_id = uuid.uuid4()
        location_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        loc_mock = _make_location_entity(location_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.LocationRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=loc_mock)
            repo_instance.count_material_references = AsyncMock(return_value=0)
            repo_instance.count_active_children = AsyncMock(return_value=m)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/locations/{location_id}",
                headers=headers,
            )

        assert response.status_code == 409, (
            f"Expected 409 Conflict for location with {m} active child(ren), "
            f"got {response.status_code}. Body: {response.text}"
        )

    @given(
        n=st.integers(min_value=1, max_value=5),
        m=st.integers(min_value=1, max_value=5),
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_delete_with_both_references_returns_409(
        self,
        n: int,
        m: int,
        async_client,
    ):
        """Property 3C: DELETE with both material references AND children returns 409.

        **Validates: Requirements 7.1, 7.2**
        """
        tenant_id = uuid.uuid4()
        location_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        loc_mock = _make_location_entity(location_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.LocationRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=loc_mock)
            repo_instance.count_material_references = AsyncMock(return_value=n)
            repo_instance.count_active_children = AsyncMock(return_value=m)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/locations/{location_id}",
                headers=headers,
            )

        assert response.status_code == 409, (
            f"Expected 409 Conflict for location with {n} material refs and {m} children, "
            f"got {response.status_code}. Body: {response.text}"
        )

    @given(n=st.just(0))
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_delete_with_zero_references_returns_204(
        self,
        n: int,
        async_client,
    ):
        """Property 3D: DELETE with no material refs and no children returns 204.

        **Validates: Requirements 7.1**
        """
        tenant_id = uuid.uuid4()
        location_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        loc_mock = _make_location_entity(location_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.LocationRepository"
            ) as MockRepo,
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.SQLAlchemyUnitOfWork"
            ) as MockUoW,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=loc_mock)
            repo_instance.count_material_references = AsyncMock(return_value=0)
            repo_instance.count_active_children = AsyncMock(return_value=0)
            repo_instance.save = AsyncMock(return_value=None)

            MockUoW.return_value.__aenter__ = AsyncMock(return_value=MockUoW.return_value)
            MockUoW.return_value.commit = AsyncMock(return_value=None)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/locations/{location_id}",
                headers=headers,
            )

        assert response.status_code == 204, (
            f"Expected 204 No Content for location with 0 references and 0 children, "
            f"got {response.status_code}. Body: {response.text}"
        )
