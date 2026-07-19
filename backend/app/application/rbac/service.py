from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.shared.permissions import ROLE_PERMISSIONS, Permission, permission_grants
from backend.app.infrastructure.persistence.models.rbac_models import (
    TenantRoleModel,
    TenantRolePermissionModel,
)


ROLE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,49}$")


def normalize_role_name(value: str) -> str:
    return str(value or "").strip().lower()


def _permission_value(permission: Permission | str) -> str:
    return permission.value if isinstance(permission, Permission) else str(permission)


def all_permission_values() -> list[str]:
    values = {permission.value for permission in Permission}
    for permissions in ROLE_PERMISSIONS.values():
        values.update(_permission_value(permission) for permission in permissions)
    return sorted(values)


def default_permissions_for_role(role_name: str) -> set[str]:
    return {
        _permission_value(permission)
        for permission in ROLE_PERMISSIONS.get(normalize_role_name(role_name), frozenset())
    }


@dataclass(frozen=True)
class EffectiveRolePermissions:
    role: str
    permissions: set[str]
    source: str

    @property
    def has_all(self) -> bool:
        return Permission.ALL.value in self.permissions

    def allows(self, permission: str) -> bool:
        return self.has_all or any(
            permission_grants(granted, permission) for granted in self.permissions
        )


async def get_effective_role_permissions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role_name: str,
) -> EffectiveRolePermissions:
    """Return DB-managed role permissions, falling back to built-in defaults."""
    normalized = normalize_role_name(role_name)
    try:
        role = await session.scalar(
            select(TenantRoleModel).where(
                TenantRoleModel.tenant_id == tenant_id,
                TenantRoleModel.name == normalized,
                TenantRoleModel.is_active.is_(True),
            )
        )
    except SQLAlchemyError:
        try:
            await session.rollback()
        except SQLAlchemyError:
            pass
        role = None

    if role is not None:
        permissions = set(await _permission_strings_for_role(session, role.id))
        return EffectiveRolePermissions(role=normalized, permissions=permissions, source="database")

    return EffectiveRolePermissions(
        role=normalized,
        permissions=default_permissions_for_role(normalized),
        source="default",
    )


async def role_has_permission(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role_name: str,
    permission: str,
) -> bool:
    effective = await get_effective_role_permissions(session, tenant_id, role_name)
    return effective.allows(permission)


async def ensure_default_roles(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Materialize built-in roles for an admin-editable tenant RBAC baseline."""
    existing = {
        row[0]
        for row in (
            await session.execute(select(TenantRoleModel.name).where(TenantRoleModel.tenant_id == tenant_id))
        ).all()
    }
    for role_name, permissions in ROLE_PERMISSIONS.items():
        if role_name in existing:
            continue
        role = TenantRoleModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=role_name,
            label=role_name.replace("_", " ").title(),
            description="Built-in ERP role",
            is_system=True,
            is_active=True,
        )
        session.add(role)
        await session.flush()
        for permission in permissions:
            session.add(
                TenantRolePermissionModel(
                    id=uuid.uuid4(),
                    role_id=role.id,
                    permission=_permission_value(permission),
                )
            )
    await session.commit()


async def list_roles(session: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    await ensure_default_roles(session, tenant_id)
    rows = (
        await session.execute(
            select(TenantRoleModel)
            .where(TenantRoleModel.tenant_id == tenant_id)
            .order_by(TenantRoleModel.is_system.desc(), TenantRoleModel.name.asc())
        )
    ).scalars().all()
    return [await serialize_role(session, row) for row in rows]


async def create_role(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    label: str | None,
    description: str | None,
    permissions: Iterable[str],
) -> dict:
    normalized = normalize_role_name(name)
    if not ROLE_NAME_PATTERN.match(normalized):
        raise ValueError("Role name must use lowercase letters, numbers, and underscores")

    existing = await session.scalar(
        select(TenantRoleModel.id).where(TenantRoleModel.tenant_id == tenant_id, TenantRoleModel.name == normalized)
    )
    if existing:
        raise ValueError(f"Role '{normalized}' already exists")

    role = TenantRoleModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=normalized,
        label=label or normalized.replace("_", " ").title(),
        description=description,
        is_system=False,
        is_active=True,
    )
    session.add(role)
    await session.flush()
    await replace_role_permissions(session, role.id, permissions)
    await session.commit()
    await session.refresh(role)
    return await serialize_role(session, role)


async def update_role_permissions(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role_name: str,
    permissions: Iterable[str],
) -> dict:
    await ensure_default_roles(session, tenant_id)
    normalized = normalize_role_name(role_name)
    role = await session.scalar(
        select(TenantRoleModel).where(TenantRoleModel.tenant_id == tenant_id, TenantRoleModel.name == normalized)
    )
    if role is None:
        raise ValueError(f"Role '{normalized}' not found")
    await replace_role_permissions(session, role.id, permissions)
    await session.commit()
    await session.refresh(role)
    return await serialize_role(session, role)


async def replace_role_permissions(
    session: AsyncSession,
    role_id: uuid.UUID,
    permissions: Iterable[str],
) -> None:
    clean = sorted({str(permission).strip() for permission in permissions if str(permission).strip()})
    if not clean:
        raise ValueError("Role must have at least one permission")

    await session.execute(delete(TenantRolePermissionModel).where(TenantRolePermissionModel.role_id == role_id))
    for permission in clean:
        session.add(
            TenantRolePermissionModel(
                id=uuid.uuid4(),
                role_id=role_id,
                permission=permission,
            )
        )


async def _permission_strings_for_role(session: AsyncSession, role_id: uuid.UUID) -> list[str]:
    rows = await session.execute(
        select(TenantRolePermissionModel.permission)
        .where(TenantRolePermissionModel.role_id == role_id)
        .order_by(TenantRolePermissionModel.permission.asc())
    )
    return [row[0] for row in rows.all()]


async def serialize_role(session: AsyncSession, role: TenantRoleModel) -> dict:
    permissions = await _permission_strings_for_role(session, role.id)
    return {
        "id": str(role.id),
        "tenant_id": str(role.tenant_id),
        "name": role.name,
        "label": role.label,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "permissions": permissions,
        "permission_count": len(permissions),
    }
