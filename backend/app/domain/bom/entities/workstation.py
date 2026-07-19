import uuid
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class Workstation(BaseEntity):
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        code: str,
        name: str,
        capacity_hours_per_day: float = 8.0,
        hourly_rate: float = 0.0,
        is_active: bool = True,
        **kwargs
    ):
        super().__init__(id=id, tenant_id=tenant_id, **kwargs)
        if not code or not name:
            raise ValueError("Workstation code and name are required.")
        if capacity_hours_per_day <= 0:
            raise ValueError("Capacity hours per day must be positive.")
        if hourly_rate < 0:
            raise ValueError("Hourly rate cannot be negative.")

        self.code = code
        self.name = name
        self.capacity_hours_per_day = capacity_hours_per_day
        self.hourly_rate = hourly_rate
        self.is_active = is_active

    def activate(self):
        self.is_active = True
        self._touch()

    def deactivate(self):
        self.is_active = False
        self._touch()

    def update(
        self,
        *,
        code: Optional[str] = None,
        name: Optional[str] = None,
        capacity_hours_per_day: Optional[float] = None,
        hourly_rate: Optional[float] = None,
        is_active: Optional[bool] = None,
    ):
        if code is not None:
            if not code.strip(): raise ValueError("Code cannot be empty.")
            self.code = code
        if name is not None:
            if not name.strip(): raise ValueError("Name cannot be empty.")
            self.name = name
        if capacity_hours_per_day is not None:
            if capacity_hours_per_day <= 0: raise ValueError("Capacity must be > 0.")
            self.capacity_hours_per_day = capacity_hours_per_day
        if hourly_rate is not None:
            if hourly_rate < 0: raise ValueError("Rate cannot be < 0.")
            self.hourly_rate = hourly_rate
        if is_active is not None:
            self.is_active = is_active
        self._touch()

    def soft_delete(self):
        from datetime import datetime, timezone
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self._touch()
