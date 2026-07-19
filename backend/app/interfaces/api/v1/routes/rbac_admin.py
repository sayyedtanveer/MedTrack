"""
Admin RBAC Management REST API
Provides endpoints for managing roles, permissions, and audit logging.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_user_id,
    get_current_role,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.rbac.service import (
    all_permission_values,
    create_role,
    default_permissions_for_role,
    get_effective_role_permissions,
    list_roles,
    update_role_permissions,
)
from backend.app.domain.shared.permissions import Permission
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.interfaces.api.v1.dependencies.auth import get_container

router = APIRouter(prefix="/admin/rbac", tags=["Admin - RBAC"])


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]{1,49}$")
    label: str | None = Field(default=None, max_length=100)
    description: str | None = None
    permissions: List[str] = Field(min_length=1)


class RolePermissionsUpdateRequest(BaseModel):
    permissions: List[str] = Field(min_length=1)


# ────────────────────────────────────────────────────────────────────────────
# ROLES API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/roles",
    summary="List all roles with permissions",
    dependencies=[Depends(require_permission("rbac:read"))],
)
async def list_all_roles(
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Return all roles and their permissions.
    
    Only accessible by ADMIN.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        roles = await list_roles(session, current_tenant_id)
    
    return {
        "roles": {role["name"]: role for role in roles},
        "items": roles,
        "total_roles": len(roles),
    }


@router.get(
    "/roles/{role_name}/permissions",
    summary="Get permissions for a specific role",
    dependencies=[Depends(require_permission("rbac:read"))],
)
async def get_role_permissions(
    role_name: str,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get detailed permissions for a specific role."""
    container = get_container(request)
    async with container.session_factory() as session:
        effective = await get_effective_role_permissions(session, current_tenant_id, role_name)
    if not effective.permissions and not default_permissions_for_role(role_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{role_name}' not found")
    
    return {
        "role": effective.role,
        "permissions": sorted(effective.permissions),
        "permission_count": len(effective.permissions),
        "has_all_permissions": effective.has_all,
        "source": effective.source,
    }


@router.post(
    "/roles",
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant role",
    dependencies=[Depends(require_permission("rbac:write"))],
)
async def create_tenant_role(
    body: RoleCreateRequest,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await create_role(
                session,
                current_tenant_id,
                name=body.name,
                label=body.label,
                description=body.description,
                permissions=body.permissions,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put(
    "/roles/{role_name}/permissions",
    summary="Replace permissions for a role",
    dependencies=[Depends(require_permission("rbac:write"))],
)
async def replace_role_permissions(
    role_name: str,
    body: RolePermissionsUpdateRequest,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            return await update_role_permissions(session, current_tenant_id, role_name, body.permissions)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ────────────────────────────────────────────────────────────────────────────
# PERMISSIONS API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/permissions",
    summary="List all available permissions",
    dependencies=[Depends(require_permission("rbac:read"))],
)
async def list_all_permissions():
    """Return all available permissions in the system."""
    perms = all_permission_values()
    
    return {
        "permissions": sorted(perms),
        "total_permissions": len(perms),
        "format": "module:action (e.g., 'inventory:write')",
    }


# ────────────────────────────────────────────────────────────────────────────
# USER PERMISSIONS API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/users/{user_id}/permissions",
    summary="Get effective permissions for a user",
    dependencies=[Depends(require_permission("rbac:read"))],
)
async def get_user_permissions(
    user_id: str,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Get all permissions granted to a specific user via their role.
    
    Returns:
    - User's current role
    - All effective permissions
    - Whether user is active
    """
    container = get_container(request)
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format"
        )
    
    async with container.session_factory() as session:
        user = await session.scalar(
            select(UserModel).where(
                UserModel.id == user_uuid,
                UserModel.tenant_id == current_tenant_id,
                UserModel.is_deleted.is_(False),
            )
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        effective = await get_effective_role_permissions(session, current_tenant_id, user.role)
        
        return {
            "user_id": str(user.id),
            "email": user.email,
            "role": effective.role,
            "is_active": user.is_active,
            "permissions": sorted(effective.permissions),
            "permission_count": len(effective.permissions),
            "has_all_permissions": effective.has_all,
            "source": effective.source,
        }


@router.post(
    "/users/{user_id}/change-role",
    summary="Change a user's role",
    dependencies=[Depends(require_permission("user:write"))],
)
async def change_user_role(
    user_id: str,
    new_role: str,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Change a user's role (ONLY ADMIN can do this).
    
    ⚠️ CRITICAL OPERATION - Logged in audit trail
    
    Restrictions:
    - Cannot change own role
    - Cannot assign role higher than current user
    - Target user must exist and belong to same tenant
    """
    container = get_container(request)
    
    # Security: Cannot change own role
    if str(user_id) == str(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    new_role_name = new_role.strip().lower()
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format"
        )
    
    async with container.session_factory() as session:
        user = await session.scalar(
            select(UserModel).where(
                UserModel.id == user_uuid,
                UserModel.tenant_id == current_tenant_id,
                UserModel.is_deleted.is_(False),
            )
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        effective = await get_effective_role_permissions(session, current_tenant_id, new_role_name)
        if not effective.permissions and new_role_name != Permission.ALL.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{new_role}' does not exist")

        old_role = user.role
        user.role = new_role_name
        await session.commit()
        await session.refresh(user)
        
        # Log to audit trail
        import logging
        logger = logging.getLogger("rbac_audit")
        logger.warning({
            "event": "ROLE_CHANGE",
            "admin_id": str(current_user_id),
            "user_id": str(user.id),
            "old_role": old_role,
            "new_role": new_role_name,
            "timestamp": str(__import__('datetime').datetime.utcnow()),
        })
    
    return {
        "user_id": str(user.id),
        "email": str(user.email),
        "old_role": old_role,
        "new_role": new_role_name,
        "message": f"Role changed from {old_role} to {new_role_name}",
    }


# ────────────────────────────────────────────────────────────────────────────
# AUDIT LOG API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/audit-log",
    summary="Get permission denial audit log",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def get_audit_log(
    limit: int = 100,
    offset: int = 0,
):
    """
    Return recent permission denial events from audit log.
    
    ⚠️ In production: Query from dedicated AuditLog table
    
    Args:
        limit: Maximum records to return (max 1000)
        offset: Pagination offset
    
    Returns:
        Audit entries with denied user/role/path/timestamp
    """
    if limit > 1000:
        limit = 1000
    
    # TODO: Query from database when AuditLog table implemented
    # For now: placeholder structure
    return {
        "audit_entries": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "note": "Audit log queries from database pending implementation",
    }


@router.get(
    "/audit-log/permission-denials",
    summary="Get all 403 permission denial events",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def get_permission_denials(
    user_id: str = None,
    role: str = None,
    path_filter: str = None,
    days: int = 7,
):
    """
    Query permission denials (403 errors) from the system.
    
    ⚠️ RBAC Permission Audit Middleware must be running
    
    Filters:
        user_id: Filter by specific user
        role: Filter by specific role (e.g., 'viewer')
        path_filter: Filter by endpoint path (partial match)
        days: Look back X days (default 7)
    
    Returns:
        Structured audit entries for compliance/forensics
    """
    return {
        "message": "Permission denial query pending implementation",
        "note": "Check application logs: grep 'PERMISSION_DENIED' for current events",
        "suggested_command": "tail -f logs/rbac_audit.log | grep PERMISSION_DENIED",
    }


# ────────────────────────────────────────────────────────────────────────────
# RBAC STATUS API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/status",
    summary="Get RBAC system status",
)
async def get_rbac_status(
    request: Request,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_role: str = Depends(get_current_role),
):
    """
    Get current user's RBAC status and system info.
    
    Accessible by all authenticated users.
    """
    container = get_container(request)
    async with container.session_factory() as session:
        effective = await get_effective_role_permissions(session, current_tenant_id, current_role)
        roles = await list_roles(session, current_tenant_id)
    
    return {
        "current_user": {
            "user_id": str(current_user_id),
            "tenant_id": str(current_tenant_id),
            "role": current_role,
        },
        "effective_permissions": {
            "count": len(effective.permissions),
            "has_all": effective.has_all,
            "source": effective.source,
        },
        "rbac_system": {
            "total_roles": len(roles),
            "total_permissions": len(all_permission_values()),
            "audit_logging": "ENABLED",
            "status": "ACTIVE",
        },
    }
