from __future__ import annotations

import uuid
from abc import abstractmethod
from typing import Optional

from backend.app.domain.shared.interfaces.repository_interface import IRepository
from backend.app.domain.tenant.entities.tenant import Tenant


class ITenantRepository(IRepository[Tenant]):
    """Repository interface for the Tenant aggregate root."""

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Return active tenant by URL slug, or None."""
        ...

    @abstractmethod
    async def slug_exists(self, slug: str) -> bool:
        """Return True if the slug is already taken (including deleted)."""
        ...
