from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class LocationType(str, Enum):
    WAREHOUSE = "warehouse"
    RACK = "rack"
    BIN = "bin"
    QUARANTINE = "quarantine"
    SUBCONTRACTOR = "subcontractor"
    PRODUCTION = "production"
    SHIPPING = "shipping"


class Location(BaseEntity):
    """
    Hierarchical storage location (warehouse -> rack -> bin).
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        name: str,
        location_type: LocationType,
        parent_location_id: Optional[uuid.UUID] = None,
        code: Optional[str] = None,
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
        self._location_type = location_type
        self._parent_location_id = parent_location_id
        self._code = code
        self._is_active = is_active

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self._touch()

    @property
    def location_type(self) -> LocationType:
        return self._location_type

    @property
    def parent_location_id(self) -> Optional[uuid.UUID]:
        return self._parent_location_id

    @parent_location_id.setter
    def parent_location_id(self, value: Optional[uuid.UUID]) -> None:
        self._parent_location_id = value
        self._touch()

    @property
    def code(self) -> Optional[str]:
        return self._code

    @code.setter
    def code(self, value: Optional[str]) -> None:
        self._code = value
        self._touch()

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = value
        self._touch()
