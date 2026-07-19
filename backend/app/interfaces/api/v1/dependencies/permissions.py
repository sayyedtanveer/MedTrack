from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from backend.app.application.rbac.service import role_has_permission
from backend.app.domain.shared.permissions import has_permission
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.interfaces.api.v1.dependencies.auth import get_current_role, get_current_tenant_id


def require_permission(permission: str) -> Callable:
    """
    FastAPI dependency factory — raises 403 if role lacks the permission.

    Usage:
        @router.get("/inventory", dependencies=[Depends(require_permission("inventory:read"))])
    """
    async def _check(
        request: Request,
        role: str = Depends(get_current_role),
        tenant_id=Depends(get_current_tenant_id),
    ) -> None:
        allowed = False
        try:
            session_factory = request.app.state.container.session_factory
            async with session_factory() as session:
                allowed = await role_has_permission(session, tenant_id, role, permission)
        except Exception:
            # Keep legacy/static RBAC working if dynamic RBAC tables are not migrated yet.
            allowed = has_permission(role, permission)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required",
            )
    return _check


def require_role(required_role: Role) -> Callable:
    """
    FastAPI dependency factory — raises 403 if user's role is not the required role.

    Usage:
        @router.delete("/tenants/{id}", dependencies=[Depends(require_role(Role.ADMIN))])
    """
    async def _check(role: str = Depends(get_current_role)) -> None:
        try:
            user_role = Role(role)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role")

        role_hierarchy = {
            Role.ADMIN: 100,
            Role.TENANT_ADMIN: 99,
            Role.MANAGER: 50,
            Role.PLANNER: 45,
            Role.SALES: 40,
            Role.STOREKEEPER: 35,
            Role.OPERATOR: 30,
            Role.QC: 28,
            Role.WORKER: 25,
            Role.VIEWER: 10,
            Role.CLIENT: 8,
            Role.SUPPLIER: 5,
        }
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 100):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' or higher required",
            )
    return _check
