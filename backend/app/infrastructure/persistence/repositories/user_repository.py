from __future__ import annotations

import uuid
from typing import Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.tenant.entities.user import User
from backend.app.domain.tenant.repositories.user_repository_interface import IUserRepository
from backend.app.domain.tenant.value_objects.email import Email
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User, UserModel], IUserRepository):

    def _model_class(self) -> Type[UserModel]:
        return UserModel

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            tenant_id=model.tenant_id,
            email=Email(address=model.email),
            hashed_password=model.hashed_password,
            first_name=model.first_name,
            last_name=model.last_name,
            role=str(model.role or Role.OPERATOR.value).lower(),
            supplier_id=model.supplier_id,
            client_id=model.client_id,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            email=str(entity.email),
            hashed_password=entity.hashed_password,
            first_name=entity.first_name,
            last_name=entity.last_name,
            role=entity.role,
            supplier_id=entity.supplier_id,
            client_id=entity.client_id,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_email(self, email: Email, tenant_id: uuid.UUID) -> Optional[User]:
        stmt = select(UserModel).where(
            UserModel.email == str(email),
            UserModel.tenant_id == tenant_id,
            UserModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_supplier_id_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[uuid.UUID]:
        stmt = select(UserModel.supplier_id).where(
            UserModel.id == user_id,
            UserModel.tenant_id == tenant_id,
            UserModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_client_id_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[uuid.UUID]:
        stmt = select(UserModel.client_id).where(
            UserModel.id == user_id,
            UserModel.tenant_id == tenant_id,
            UserModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: Email, tenant_id: uuid.UUID) -> bool:
        stmt = select(UserModel.id).where(
            UserModel.email == str(email),
            UserModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_email_and_tenant(self, email: str, tenant_id: uuid.UUID) -> Optional[User]:
        """
        Convenience method to get user by email (string) and tenant_id.
        Used primarily by 2FA and login flows.
        
        Args:
            email: User email address (string)
            tenant_id: Tenant UUID
            
        Returns:
            User entity if found and not deleted, None otherwise
        """
        stmt = select(UserModel).where(
            UserModel.email == email,
            UserModel.tenant_id == tenant_id,
            UserModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
