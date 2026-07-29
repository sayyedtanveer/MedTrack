from __future__ import annotations

from enum import Enum


class TenantStatus(str, Enum):
    """
    Tenant lifecycle status.
    """

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "TenantStatus":
        try:
            return cls(value.lower())
        except ValueError:
            valid = [s.value for s in cls]
            raise ValueError(f"Invalid status '{value}'. Must be one of: {valid}")
