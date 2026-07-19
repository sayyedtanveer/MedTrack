from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class MaterialCategory(BaseEntity):
    """
    Categorization of materials for reporting and hierarchical organization.
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        name: str,
        code_prefix: str = "GEN",
        description: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._name = name
        self._code_prefix = code_prefix
        self._description = description
        self._is_active = is_active

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self._touch()

    @property
    def code_prefix(self) -> str:
        return self._code_prefix

    @code_prefix.setter
    def code_prefix(self, value: str) -> None:
        self._code_prefix = value
        self._touch()

    @property
    def description(self) -> Optional[str]:
        return self._description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        self._description = value
        self._touch()

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = value
        self._touch()
