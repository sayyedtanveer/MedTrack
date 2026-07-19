from __future__ import annotations

import uuid
from abc import abstractmethod

from backend.app.domain.shared.interfaces.domain_service_interface import IDomainService
from backend.app.domain.tenant.entities.user import User


class IAuthenticationService(IDomainService):
    """
    Domain service interface for credential verification.

    Kept in the domain layer as an interface — the concrete implementation
    that uses bcrypt lives in infrastructure/security/.
    """

    @abstractmethod
    def verify_credentials(self, user: User, plain_password: str) -> bool:
        """Return True if plain_password matches the user's hashed password."""
        ...
