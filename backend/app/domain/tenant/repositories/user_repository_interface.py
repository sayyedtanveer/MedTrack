from __future__ import annotations

import uuid
from abc import abstractmethod
from typing import Optional

from backend.app.domain.shared.interfaces.repository_interface import IRepository
from backend.app.domain.tenant.entities.user import User
from backend.app.domain.tenant.value_objects.email import Email


class IUserRepository(IRepository[User]):
    """Repository interface for the User entity."""

    @abstractmethod
    async def get_by_email(
        self, email: Email, tenant_id: uuid.UUID
    ) -> Optional[User]:
        """Return active user by email within a tenant, or None."""
        ...

    @abstractmethod
    async def email_exists(
        self, email: Email, tenant_id: uuid.UUID
    ) -> bool:
        """Return True if email is already registered in this tenant."""
        ...

    @abstractmethod
    async def get_supplier_id_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[uuid.UUID]:
        """Return the supplier_id linked to this user, or None if not a supplier."""
        ...

    @abstractmethod
    async def get_client_id_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[uuid.UUID]:
        """Return the client_id linked to this user, or None if not a client portal user."""
        ...
