from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException
from backend.app.domain.tenant.value_objects.email import Email
from backend.app.domain.tenant.value_objects.role import Role


class User(BaseEntity):
    """
    User entity — belongs to a Tenant.

    A user has credentials, a role, and belongs to exactly one tenant.
    Password is always stored hashed — never plaintext.
    """

    def __init__(
        self,
        tenant_id: uuid.UUID,
        email: Email,
        hashed_password: str,
        first_name: str,
        last_name: str,
        role: Role | str = Role.OPERATOR,
        supplier_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        is_active: bool = True,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )
        self._email = email
        self._hashed_password = hashed_password
        self._first_name = first_name
        self._last_name = last_name
        self._role = self._normalize_role(role)
        self._supplier_id = supplier_id
        self._client_id = client_id
        self._is_active = is_active

        self._validate()

    # ── Properties ────────────────────────────────────────────────────────
    @property
    def email(self) -> Email:
        return self._email

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def full_name(self) -> str:
        return f"{self._first_name} {self._last_name}"

    @property
    def role(self) -> str:
        return self._role

    @property
    def supplier_id(self) -> Optional[uuid.UUID]:
        return self._supplier_id

    @property
    def client_id(self) -> Optional[uuid.UUID]:
        return self._client_id

    @property
    def is_active(self) -> bool:
        return self._is_active

    # ── Invariants ────────────────────────────────────────────────────────
    def _validate(self) -> None:
        if not self._first_name or len(self._first_name.strip()) < 1:
            raise BusinessRuleViolationException(rule="First name cannot be empty")
        if not self._hashed_password:
            raise BusinessRuleViolationException(rule="Password cannot be empty")

    # ── Behaviour ─────────────────────────────────────────────────────────
    def change_role(self, new_role: Role | str) -> None:
        self._role = self._normalize_role(new_role)
        self._touch()

    def update_password(self, new_hashed_password: str) -> None:
        if not new_hashed_password:
            raise BusinessRuleViolationException(rule="Hashed password cannot be empty")
        self._hashed_password = new_hashed_password
        self._touch()

    def activate(self) -> None:
        self._is_active = True
        self._touch()

    def deactivate(self) -> None:
        self._is_active = False
        self._touch()

    @staticmethod
    def _normalize_role(role: Role | str) -> str:
        value = role.value if isinstance(role, Role) else str(role)
        return value.strip().lower()
