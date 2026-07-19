from __future__ import annotations

from abc import abstractmethod
from typing import Optional

import bcrypt

from backend.app.domain.tenant.services.authentication_service import IAuthenticationService
from backend.app.domain.tenant.entities.user import User


class IPasswordHasher:
    """Interface for password hashing. Swappable implementation."""

    @abstractmethod
    def hash(self, plain_password: str) -> str: ...

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool: ...


class BcryptPasswordHasher(IPasswordHasher, IAuthenticationService):
    """bcrypt-based password hasher. Implements both service interfaces."""

    def hash(self, plain_password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain_password.encode(), salt).decode()

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        except Exception:
            return False

    def verify_credentials(self, user: User, plain_password: str) -> bool:
        return self.verify(plain_password, user.hashed_password)
