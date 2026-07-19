from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.domain.shared.base_value_object import BaseValueObject
from backend.app.domain.shared.exceptions.domain_exception import DomainException

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


@dataclass(frozen=True)
class Email(BaseValueObject):
    """
    Email value object — validates format on construction.

    Usage:
        email = Email(address="admin@acme.com")
        email.address  # → "admin@acme.com"
    """

    address: str

    def __post_init__(self) -> None:
        # Normalize before validation
        object.__setattr__(self, "address", self.address.strip().lower())
        super().__post_init__()

    def _validate(self) -> None:
        if not self.address:
            raise DomainException("Email address cannot be empty", code="INVALID_EMAIL")
        if not _EMAIL_REGEX.match(self.address):
            raise DomainException(
                f"'{self.address}' is not a valid email address", code="INVALID_EMAIL"
            )

    def domain(self) -> str:
        """Return the domain part of the email."""
        return self.address.split("@")[1]

    def __str__(self) -> str:
        return self.address
