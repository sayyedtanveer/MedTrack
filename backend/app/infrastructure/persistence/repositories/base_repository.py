from __future__ import annotations

import uuid
from abc import abstractmethod
from datetime import datetime, timezone
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.shared.base_entity import BaseEntity
from backend.app.domain.shared.interfaces.repository_interface import IRepository

TEntity = TypeVar("TEntity", bound=BaseEntity)
TModel = TypeVar("TModel")


class BaseRepository(IRepository[TEntity], Generic[TEntity, TModel]):
    """
    Abstract base repository — eliminates CRUD boilerplate across all
    bounded contexts.

    Automatically applies:
    - Tenant isolation: WHERE tenant_id = :tenant_id
    - Soft-delete filtering: WHERE is_deleted = false

    Subclasses only need to implement the three mapping hooks.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Abstract Mapping Hooks ────────────────────────────────────────────
    @abstractmethod
    def _to_entity(self, model: TModel) -> TEntity:
        """Convert ORM model → domain entity."""
        ...

    @abstractmethod
    def _to_model(self, entity: TEntity) -> TModel:
        """Convert domain entity → ORM model."""
        ...

    @abstractmethod
    def _model_class(self) -> Type[TModel]:
        """Return the SQLAlchemy model class."""
        ...

    # ── IRepository Implementation ────────────────────────────────────────
    async def get_by_id(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[TEntity]:
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().id == id,
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_including_deleted(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[TEntity]:
        """Admin-only: returns entity even if soft-deleted."""
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().id == id,
                self._model_class().tenant_id == tenant_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, entity: TEntity) -> TEntity:
        model = self._to_model(entity)
        await self._session.merge(model)
        await self._session.flush()
        return entity

    async def delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Soft-delete: sets is_deleted=True, deleted_at=now."""
        stmt = (
            update(self._model_class())
            .where(
                self._model_class().id == id,
                self._model_class().tenant_id == tenant_id,
            )
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self._session.execute(stmt)

    async def list(
        self,
        tenant_id: uuid.UUID,
        filters: Optional[dict] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[TEntity]:
        offset = (page - 1) * page_size
        stmt = (
            select(self._model_class())
            .where(
                self._model_class().tenant_id == tenant_id,
                self._model_class().is_deleted.is_(False),
            )
            .offset(offset)
            .limit(page_size)
            .order_by(self._model_class().created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
