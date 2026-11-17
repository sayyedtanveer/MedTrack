from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException

from backend.app.application.rbac.service import EffectiveRolePermissions
from backend.app.application.inventory.commands.inventory_commands import (
    UpdateMaterialCommand,
)
from backend.app.application.inventory.handlers.inventory_handlers import (
    UpdateMaterialHandler,
)
from backend.app.domain.inventory.entities.material import Material, MaterialType
from backend.app.domain.shared.permissions import Permission, has_permission
from backend.app.interfaces.api.v1.router import api_v1_router
from backend.app.interfaces.api.v1.dependencies import permissions


def test_pricing_routes_mount_once_under_api_v1() -> None:
    app = FastAPI()
    app.include_router(api_v1_router, prefix="/api/v1")
    paths = {route.path for route in app.routes}

    assert "/api/v1/procurement/pricing/supplier-price-agreements" in paths
    assert "/api/v1/procurement/pricing/cost-revisions" in paths
    assert not any(path.startswith("/api/v1/api/v1/procurement/pricing") for path in paths)

    pricing_routes = [
        route
        for route in app.routes
        if route.path.startswith("/api/v1/procurement/pricing/")
    ]
    assert pricing_routes
    assert all(
        any(dependency.call.__name__ == "_check" for dependency in route.dependant.dependencies)
        for route in pricing_routes
    )


def test_pricing_openapi_contracts_match_frontend_requests_and_responses() -> None:
    app = FastAPI()
    app.include_router(api_v1_router, prefix="/api/v1")
    openapi = app.openapi()

    agreement_list = openapi["paths"][
        "/api/v1/procurement/pricing/supplier-price-agreements"
    ]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert agreement_list["$ref"].endswith("/ListSupplierAgreementsResponse")
    agreement_filters = openapi["paths"][
        "/api/v1/procurement/pricing/supplier-price-agreements"
    ]["get"]["parameters"]
    assert "status" in {parameter["name"] for parameter in agreement_filters}

    submit = openapi["paths"][
        "/api/v1/procurement/pricing/supplier-price-agreements/{agreement_id}/submit-for-approval"
    ]["post"]
    assert "requestBody" not in submit

    active_agreement_params = openapi["paths"][
        "/api/v1/procurement/pricing/active-price-agreement"
    ]["get"]["parameters"]
    assert {
        parameter["name"]
        for parameter in active_agreement_params
        if parameter.get("required")
    } == {"supplier_id", "material_id"}

    create_revision = openapi["components"]["schemas"]["CreateCostRevisionRequest"]
    assert "requested_cost" in create_revision["properties"]
    assert "proposed_cost" not in create_revision["properties"]


def test_pricing_permissions_reuse_legacy_grants_without_granting_supplier_access() -> None:
    assert has_permission("viewer", Permission.PROCUREMENT_PRICING_READ.value)
    assert has_permission("manager", Permission.PROCUREMENT_PRICING_AGREEMENT_WRITE.value)
    assert has_permission("manager", Permission.PROCUREMENT_PRICING_APPROVE.value)
    assert not has_permission("operator", Permission.PROCUREMENT_PRICING_APPROVE.value)
    assert not has_permission("supplier", Permission.PROCUREMENT_PRICING_READ.value)
    assert not has_permission("supplier", Permission.PROCUREMENT_PRICING_OVERRIDE.value)

    explicit_supplier_grant = EffectiveRolePermissions(
        role="supplier",
        permissions={Permission.PROCUREMENT_PRICING_READ.value},
        source="database",
    )
    assert explicit_supplier_grant.allows(Permission.PROCUREMENT_PRICING_READ.value)


@pytest.mark.asyncio
async def test_permission_dependency_uses_tenant_role_and_denies_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    observed: list[tuple[object, object, str, str]] = []

    class SessionContext:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> bool:
            return False

    class SessionFactory:
        def __call__(self) -> SessionContext:
            return SessionContext()

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                container=SimpleNamespace(session_factory=SessionFactory())
            )
        )
    )

    async def deny_permission(
        session: object, received_tenant_id: object, role: str, permission: str
    ) -> bool:
        observed.append((session, received_tenant_id, role, permission))
        return False

    monkeypatch.setattr(permissions, "role_has_permission", deny_permission)
    dependency = permissions.require_permission(Permission.PROCUREMENT_PRICING_APPROVE.value)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(request, role="operator", tenant_id=tenant_id)

    assert exc_info.value.status_code == 403
    assert observed[0][1:] == (
        tenant_id,
        "operator",
        Permission.PROCUREMENT_PRICING_APPROVE.value,
    )


@pytest.mark.asyncio
async def test_ordinary_material_update_cannot_set_approved_standard_cost() -> None:
    material_id = uuid4()
    tenant_id = uuid4()
    material = Material(
        id=material_id,
        tenant_id=tenant_id,
        code="RM-TEST-001",
        name="Test Material",
        material_type=MaterialType.RAW,
    )
    repository = SimpleNamespace(get_by_id=AsyncMock(return_value=material))
    handler = UpdateMaterialHandler(material_repo=repository, uow=object())

    with pytest.raises(ValueError, match="Direct material cost updates are not allowed"):
        await handler.handle(
            UpdateMaterialCommand(
                id=material_id,
                tenant_id=tenant_id,
                current_cost=Decimal("25.00"),
            )
        )

    repository.get_by_id.assert_awaited_once_with(material_id, tenant_id)
