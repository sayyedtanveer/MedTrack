from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.tenant_schemas import TenantResponse, UpdateTenantRequest
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.repositories.tenant_repository import TenantRepository

router = APIRouter(prefix="/tenants", tags=["Tenants"])

# ISO 4217 currency code whitelist
_ALLOWED_CURRENCY_CODES = {
    "INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "CNY", "AUD", "CAD",
}

# GST format: 2-digit state code + 5 letters + 4 digits + 1 letter + 1 check + Z + 1 alphanum
_GST_REGEX = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)


def _tenant_response_from_model(model: TenantModel) -> TenantResponse:
    """Build a fully-populated TenantResponse directly from the ORM model row."""
    return TenantResponse(
        id=str(model.id),
        name=model.name,
        slug=model.slug,
        plan=model.plan,
        is_active=model.is_active,
        company_name=getattr(model, "company_name", None),
        gst_number=getattr(model, "gst_number", None),
        address=getattr(model, "address", None),
        phone=getattr(model, "phone", None),
        email=getattr(model, "email", None),
        logo_url=getattr(model, "logo_url", None),
        footer_text=getattr(model, "footer_text", None),
        currency_code=getattr(model, "currency_code", None),
        currency_symbol=getattr(model, "currency_symbol", None),
        timezone=getattr(model, "timezone", None),
        default_warehouse_name=getattr(model, "default_warehouse_name", None),
    )


async def _fetch_tenant_model(session, tenant_id: uuid.UUID) -> TenantModel | None:
    """Return the raw TenantModel row (not the domain entity) or None."""
    result = await session.execute(
        select(TenantModel).where(
            TenantModel.id == tenant_id,
            TenantModel.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


# ── /me convenience routes — MUST be declared before /{tenant_id} ─────────────

@router.get(
    "/me",
    response_model=TenantResponse,
    dependencies=[Depends(require_permission("tenant:read"))],
    summary="Get current tenant profile (resolved from JWT)",
)
async def get_me(
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Resolve tenant_id from the JWT and return the full tenant profile."""
    container = get_container(request)
    async with container.session_factory() as session:
        model = await _fetch_tenant_model(session, current_tenant_id)

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return _tenant_response_from_model(model)


@router.put(
    "/me",
    response_model=TenantResponse,
    dependencies=[Depends(require_permission("tenant:write"))],
    summary="Update current tenant profile (resolved from JWT)",
)
async def update_me(
    req: UpdateTenantRequest,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Resolve tenant_id from the JWT and delegate to the update logic."""
    return await _do_update_tenant(current_tenant_id, current_tenant_id, req, request)


# ── /{tenant_id} routes ────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_permission("tenant:read"))],
    summary="Get tenant details (admin only)",
)
async def get_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    if tenant_id != current_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another tenant")

    container = get_container(request)
    async with container.session_factory() as session:
        model = await _fetch_tenant_model(session, tenant_id)

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return _tenant_response_from_model(model)


@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_permission("tenant:write"))],
    summary="Update tenant profile",
)
async def update_tenant(
    tenant_id: uuid.UUID,
    req: UpdateTenantRequest,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Update editable profile fields for a tenant. Only the tenant's own record may be updated."""
    return await _do_update_tenant(tenant_id, current_tenant_id, req, request)


# ── Shared update logic ────────────────────────────────────────────────────────

async def _do_update_tenant(
    tenant_id: uuid.UUID,
    current_tenant_id: uuid.UUID,
    req: UpdateTenantRequest,
    request: Request,
) -> TenantResponse:
    """Validate and apply a PATCH-style update to the tenant profile."""

    # 7.1 — enforce tenant isolation
    if tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update another tenant's profile",
        )

    # Server-side field validation (only when a value is provided)
    if req.gst_number is not None:
        if not _GST_REGEX.match(req.gst_number):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Invalid GST number format. Expected: "
                    "2-digit state + 5 uppercase letters + 4 digits + "
                    "1 letter + 1 check digit + Z + 1 alphanumeric "
                    "(e.g. 27AAPFU0939F1ZV)"
                ),
            )

    # Timezone validation skipped — frontend provides a curated static list of valid IANA timezones

    if req.currency_code is not None:
        if req.currency_code.upper() not in _ALLOWED_CURRENCY_CODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unsupported currency code '{req.currency_code}'. "
                    f"Allowed values: {', '.join(sorted(_ALLOWED_CURRENCY_CODES))}"
                ),
            )

    container = get_container(request)
    async with container.session_factory() as session:
        repo = TenantRepository(session)
        try:
            await repo.update(tenant_id, req.model_dump(exclude_none=True))
            await session.commit()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        # Fetch the raw model to build a fully-populated TenantResponse
        model = await _fetch_tenant_model(session, tenant_id)

    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found after update")

    return _tenant_response_from_model(model)
