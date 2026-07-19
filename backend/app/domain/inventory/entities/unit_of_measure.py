from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class UnitOfMeasure(BaseEntity):
    """
    Standard unit of measure definition.
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        code: str,
        name: str,
        precision: int = 2,
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
        self._code = code
        self._name = name
        self._precision = precision
        self._is_active = is_active

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, value: str) -> None:
        self._code = value
        self._touch()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self._touch()

    @property
    def precision(self) -> int:
        return self._precision

    @precision.setter
    def precision(self, value: int) -> None:
        self._precision = value
        self._touch()

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = value
        self._touch()
