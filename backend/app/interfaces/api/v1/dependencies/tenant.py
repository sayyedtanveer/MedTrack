from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from backend.app.domain.tenant.repositories.tenant_repository_interface import ITenantRepository
from backend.app.infrastructure.persistence.repositories.tenant_repository import TenantRepository
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container


async def get_current_tenant(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    request: Request = None,
):
    """Resolve the full Tenant entity from the JWT tenant_id claim."""
    container = get_container(request)
    async with container.session_factory() as session:
        repo = TenantRepository(session)
        tenant = await repo.get_by_id(tenant_id, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive",
        )
    return tenant
