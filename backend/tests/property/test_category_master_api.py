"""
Property-based tests for Category Master API.

**Validates: Requirements 6.1, 6.2**

Property 2 — Category Reference Integrity:
  For any category with N > 0 material references, DELETE returns HTTP 409.
  For N == 0 references, DELETE returns HTTP 204.

# Feature: master-data-audit, Property 2: Category Reference Integrity
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

def _make_category_entity(category_id: uuid.UUID, tenant_id: uuid.UUID) -> Any:
    """Return a lightweight mock that looks like a MaterialCategory domain entity."""
    cat = MagicMock()
    cat.id = category_id
    cat.tenant_id = tenant_id
    cat.name = "Test Category"
    cat.code_prefix = "TST"
    cat.description = None
    cat.is_active = True
    cat._is_deleted = False
    return cat


# ─────────────────────────────────────────────────────────────────────────────
# Property 2: Reference Integrity — DELETE returns 409 when material refs > 0
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryDeleteReferenceIntegrity:
    """**Validates: Requirements 6.1, 6.2**

    Property 2: For any N > 0 material references, DELETE /categories/{id} returns 409.
    For N == 0, DELETE returns 204.
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
        """Property 2A: DELETE a category with N > 0 active material references
        always returns 409 Conflict.

        **Validates: Requirements 6.1, 6.2**
        """
        tenant_id = uuid.uuid4()
        category_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        cat_mock = _make_category_entity(category_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.MaterialCategoryRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=cat_mock)
            repo_instance.count_material_references = AsyncMock(return_value=n)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/categories/{category_id}",
                headers=headers,
            )

        assert response.status_code == 409, (
            f"Expected 409 Conflict for category with {n} material reference(s), "
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
        """Property 2B: DELETE a category with 0 material references returns 204.

        **Validates: Requirements 6.1**
        """
        tenant_id = uuid.uuid4()
        category_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        cat_mock = _make_category_entity(category_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.MaterialCategoryRepository"
            ) as MockRepo,
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.SQLAlchemyUnitOfWork"
            ) as MockUoW,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=cat_mock)
            repo_instance.count_material_references = AsyncMock(return_value=0)
            repo_instance.update = AsyncMock(return_value=None)

            MockUoW.return_value.__aenter__ = AsyncMock(return_value=MockUoW.return_value)
            MockUoW.return_value.commit = AsyncMock(return_value=None)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/categories/{category_id}",
                headers=headers,
            )

        assert response.status_code == 204, (
            f"Expected 204 No Content for category with 0 material references, "
            f"got {response.status_code}. Body: {response.text}"
        )

    @given(n=st.integers(min_value=1, max_value=10))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_delete_409_response_mentions_count(
        self,
        n: int,
        async_client,
    ):
        """Property 2A (detail): The 409 response body mentions the material count.

        **Validates: Requirements 6.2**
        """
        tenant_id = uuid.uuid4()
        category_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        cat_mock = _make_category_entity(category_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.MaterialCategoryRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=cat_mock)
            repo_instance.count_material_references = AsyncMock(return_value=n)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/categories/{category_id}",
                headers=headers,
            )

        assert response.status_code == 409

        body = response.text
        # The detail message should include the count so the user understands why
        assert str(n) in body, (
            f"409 response body should contain the reference count ({n}). "
            f"Got body: {body}"
        )
