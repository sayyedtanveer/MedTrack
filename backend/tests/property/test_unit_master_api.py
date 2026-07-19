"""
Property-based tests for Unit Master API.

**Validates: Requirements 5.1, 5.2, 5.4**

Property 1 — Reference Integrity:
  For any unit with N > 0 material or BOM references, DELETE returns HTTP 409.
  For N == 0 references, DELETE returns HTTP 204.

Property 8 — Code Immutability:
  For any PUT request that includes a "code" field, the response is HTTP 422,
  regardless of the code value.

# Feature: master-data-audit, Properties 1 and 8: Unit Reference Integrity and Code Immutability
"""
from __future__ import annotations

import uuid
from typing import Any
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


def _admin_headers(tenant_id: uuid.UUID) -> dict[str, str]:
    """Generate admin-role JWT headers for a given tenant."""
    token = _jwt.create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        role="admin",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


# ─── Mock builders ────────────────────────────────────────────────────────────

def _make_unit_entity(unit_id: uuid.UUID, tenant_id: uuid.UUID) -> Any:
    """Return a lightweight mock that looks like a UnitOfMeasure domain entity."""
    unit = MagicMock()
    unit.id = unit_id
    unit.tenant_id = tenant_id
    unit.code = "KG"
    unit.name = "Kilogram"
    unit.precision = 3
    unit.is_active = True
    return unit


# ─────────────────────────────────────────────────────────────────────────────
# Property 1: Reference Integrity — DELETE returns 409 when refs > 0
# ─────────────────────────────────────────────────────────────────────────────


class TestUnitDeleteReferenceIntegrity:
    """**Validates: Requirements 5.1, 5.2**

    Property 1: For any N > 0 references (material or BOM), DELETE /units/{id} returns 409.
    For N == 0 references, DELETE /units/{id} returns 204.
    """

    @given(n=st.integers(min_value=1, max_value=10))
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_delete_with_references_returns_409(
        self,
        n: int,
        async_client,
    ):
        """Property 1A: DELETE a unit that has N > 0 references always returns 409.

        **Validates: Requirements 5.1, 5.2**
        """
        tenant_id = uuid.uuid4()
        unit_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        unit_mock = _make_unit_entity(unit_id, tenant_id)

        # Split N references between material and BOM counts (at least 1 total)
        mat_refs = max(1, n // 2)
        bom_refs = n - mat_refs

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.UnitOfMeasureRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=unit_mock)
            repo_instance.count_material_references = AsyncMock(return_value=mat_refs)
            repo_instance.count_bom_references = AsyncMock(return_value=bom_refs)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/units/{unit_id}",
                headers=headers,
            )

        assert response.status_code == 409, (
            f"Expected 409 Conflict for unit with {n} reference(s) (mat={mat_refs}, "
            f"bom={bom_refs}), got {response.status_code}. Body: {response.text}"
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
        """Property 1B: DELETE a unit with 0 references returns 204 No Content.

        **Validates: Requirements 5.1**
        """
        tenant_id = uuid.uuid4()
        unit_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        unit_mock = _make_unit_entity(unit_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.UnitOfMeasureRepository"
            ) as MockRepo,
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.SQLAlchemyUnitOfWork"
            ) as MockUoW,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=unit_mock)
            repo_instance.count_material_references = AsyncMock(return_value=0)
            repo_instance.count_bom_references = AsyncMock(return_value=0)
            repo_instance.update = AsyncMock(return_value=None)

            uow_instance = MockUoW.return_value.__aenter__ = AsyncMock(return_value=MockUoW.return_value)
            MockUoW.return_value.commit = AsyncMock(return_value=None)

            response = await async_client.delete(
                f"/api/v1/inventory/master-data/units/{unit_id}",
                headers=headers,
            )

        assert response.status_code == 204, (
            f"Expected 204 No Content for unit with 0 references, "
            f"got {response.status_code}. Body: {response.text}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Property 8: Code Immutability — PUT with any "code" value returns 422
# ─────────────────────────────────────────────────────────────────────────────


class TestUnitCodeImmutability:
    """**Validates: Requirements 5.4**

    Property 8: PUT /units/{id} with any body containing "code" returns 422,
    regardless of the code value.
    """

    @given(code_value=st.text(min_size=1, max_size=20))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_put_with_code_field_returns_422(
        self,
        code_value: str,
        async_client,
    ):
        """Property 8: Any PUT body with a "code" key returns HTTP 422.

        **Validates: Requirements 5.4**
        """
        tenant_id = uuid.uuid4()
        unit_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        unit_mock = _make_unit_entity(unit_id, tenant_id)

        # The route rejects "code" before touching the repository,
        # but we patch it anyway so the test is self-contained.
        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.UnitOfMeasureRepository"
            ) as MockRepo,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=unit_mock)
            repo_instance.update = AsyncMock(return_value=None)

            response = await async_client.put(
                f"/api/v1/inventory/master-data/units/{unit_id}",
                json={"code": code_value, "name": "Updated Name"},
                headers=headers,
            )

        assert response.status_code == 422, (
            f"Expected 422 Unprocessable for PUT with code='{code_value}', "
            f"got {response.status_code}. Body: {response.text}"
        )

    @given(code_value=st.text(min_size=1, max_size=20))
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None,
    )
    async def test_put_without_code_field_does_not_return_422(
        self,
        code_value: str,
        async_client,
    ):
        """Complementary check: PUT without "code" does NOT return 422 due to immutability.

        **Validates: Requirements 5.4**
        """
        tenant_id = uuid.uuid4()
        unit_id = uuid.uuid4()
        headers = _admin_headers(tenant_id)
        unit_mock = _make_unit_entity(unit_id, tenant_id)

        with (
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.UnitOfMeasureRepository"
            ) as MockRepo,
            patch(
                "backend.app.interfaces.api.v1.routes.master_data.SQLAlchemyUnitOfWork"
            ) as MockUoW,
        ):
            repo_instance = MockRepo.return_value
            repo_instance.get_by_id = AsyncMock(return_value=unit_mock)
            repo_instance.update = AsyncMock(return_value=None)
            repo_instance.count_material_references = AsyncMock(return_value=0)
            repo_instance.count_bom_references = AsyncMock(return_value=0)

            MockUoW.return_value.__aenter__ = AsyncMock(return_value=MockUoW.return_value)
            MockUoW.return_value.commit = AsyncMock(return_value=None)

            response = await async_client.put(
                f"/api/v1/inventory/master-data/units/{unit_id}",
                json={"name": "Updated Name"},
                headers=headers,
            )

        # Should not be 422 due to the immutability guard (may be 200 or other)
        assert response.status_code != 422 or "immutable" not in response.text.lower(), (
            f"PUT without 'code' field should not trigger the immutability 422, "
            f"got {response.status_code}. Body: {response.text}"
        )
