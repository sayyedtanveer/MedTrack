from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Type

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.tenant.entities.tenant import Tenant
from backend.app.domain.tenant.repositories.tenant_repository_interface import ITenantRepository
from backend.app.domain.tenant.value_objects.email import Email
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class TenantRepository(BaseRepository[Tenant, TenantModel], ITenantRepository):

    def _model_class(self) -> Type[TenantModel]:
        return TenantModel

    def _to_entity(self, model: TenantModel) -> Tenant:
        return Tenant(
            id=model.id,
            tenant_id=model.id,
            name=model.name,
            slug=model.slug,
            plan=model.plan,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            status=model.status,
            is_system_tenant=model.is_system_tenant,
            timezone=getattr(model, "timezone", None),
            default_warehouse_name=getattr(model, "default_warehouse_name", None),
        )

    def _to_model(self, entity: Tenant) -> TenantModel:
        return TenantModel(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            plan=entity.plan,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            status=entity.status.value,
            is_system_tenant=entity.is_system_tenant,
        )

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        stmt = select(TenantModel).where(
            TenantModel.slug == slug,
            TenantModel.is_deleted.is_(False),
            TenantModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_tenant_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Fetch a tenant by its own primary key (id).

        The Tenant aggregate root has no separate tenant_id column — its id IS
        the tenant_id used for all child entities. This method bypasses the
        BaseRepository.get_by_id() which incorrectly filters on a non-existent
        tenant_id column.
        """
        stmt = select(TenantModel).where(
            TenantModel.id == tenant_id,
            TenantModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(TenantModel.id).where(TenantModel.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update(self, tenant_id: uuid.UUID, fields: dict) -> Tenant:
        """PATCH update — apply only non-None fields to the tenant record.

        Raises ValueError if the tenant is not found.
        """
        # Validate the tenant exists first
        existing = await self.get_by_tenant_id(tenant_id)
        if existing is None:
            raise ValueError(f"Tenant with id '{tenant_id}' not found.")

        # Allowed profile fields for PATCH updates
        allowed_fields = {
            "company_name",
            "gst_number",
            "address",
            "phone",
            "email",
            "logo_url",
            "footer_text",
            "currency_code",
            "currency_symbol",
            "timezone",
            "default_warehouse_name",
        }

        # Filter to only non-None values that belong to the allowed set
        non_none_fields = {
            k: v for k, v in fields.items()
            if v is not None and k in allowed_fields
        }

        if non_none_fields:
            # Always bump updated_at on a write
            non_none_fields["updated_at"] = datetime.now(timezone.utc)

            stmt = (
                update(TenantModel)
                .where(TenantModel.id == tenant_id)
                .values(**non_none_fields)
            )
            await self._session.execute(stmt)
            await self._session.flush()

        # Return the fresh entity after the update
        updated = await self.get_by_tenant_id(tenant_id)
        # get_by_tenant_id only returns None when the row is deleted; since we
        # just confirmed it exists (and the update is non-destructive), this is
        # safe to assert.
        assert updated is not None
        return updated
