import uuid
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity


class Operation(BaseEntity):
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        name: str,
        workstation_id: uuid.UUID,
        setup_time: float = 0.0,
        run_time: float = 0.0,
        description: Optional[str] = None,
        is_active: bool = True,
        **kwargs
    ):
        super().__init__(id=id, tenant_id=tenant_id, **kwargs)
        if not name:
            raise ValueError("Operation name is required.")
        if not workstation_id:
            raise ValueError("Workstation ID is required.")
        if setup_time < 0:
            raise ValueError("Setup time cannot be negative.")
        if run_time < 0:
            raise ValueError("Run time cannot be negative.")
        if setup_time == 0 and run_time == 0:
            raise ValueError("Operation must have either setup time or run time.")

        self.name = name
        self.workstation_id = workstation_id
        self.setup_time = setup_time
        self.run_time = run_time
        self.description = description
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
        name: Optional[str] = None,
        workstation_id: Optional[uuid.UUID] = None,
        setup_time: Optional[float] = None,
        run_time: Optional[float] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        if name is not None:
            if not name.strip(): raise ValueError("Name cannot be empty.")
            self.name = name
        if workstation_id is not None:
            if not workstation_id: raise ValueError("Workstation ID is required.")
            self.workstation_id = workstation_id
        if setup_time is not None:
            if setup_time < 0: raise ValueError("Setup time cannot be negative.")
            self.setup_time = setup_time
        if run_time is not None:
            if run_time < 0: raise ValueError("Run time cannot be negative.")
            self.run_time = run_time
            
        if self.setup_time == 0 and self.run_time == 0:
            raise ValueError("Operation must have either setup time or run time.")
            
        if description is not None:
            self.description = description
        if is_active is not None:
            self.is_active = is_active
        self._touch()

    def soft_delete(self):
        from datetime import datetime, timezone
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self._touch()
