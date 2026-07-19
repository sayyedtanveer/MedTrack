from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from backend.app.domain.shared.base_entity import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class IRepository(ABC, Generic[T]):
    """
    Generic repository interface for aggregate roots.

    All implementations must filter by tenant_id and respect soft-delete.
    """

    @abstractmethod
    async def get_by_id(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[T]:
        """Return entity or None (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def get_including_deleted(
        self, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[T]:
        """Return entity including soft-deleted records (admin use)."""
        ...

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Insert or update the entity."""
        ...

    @abstractmethod
    async def delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Soft-delete the entity (sets is_deleted=True)."""
        ...

    @abstractmethod
    async def list(
        self,
        tenant_id: uuid.UUID,
        filters: Optional[dict] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[T]:
        """Return paginated list (excludes soft-deleted)."""
        ...
