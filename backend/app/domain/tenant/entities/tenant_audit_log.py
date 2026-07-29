from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.domain.shared.base_entity import BaseEntity
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException


class TenantAuditLog(BaseEntity):
    """
    Audit log for tenant lifecycle events (Approve, Reject, Suspend, etc.).
    """

    def __init__(
        self,
        tenant_id: uuid.UUID,
        action: str,
        reason: Optional[str] = None,
        acted_by: Optional[uuid.UUID] = None,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
        )
        self._action = action
        self._reason = reason
        self._acted_by = acted_by

        self._validate()

    @property
    def action(self) -> str:
        return self._action

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    @property
    def acted_by(self) -> Optional[uuid.UUID]:
        return self._acted_by

    def _validate(self) -> None:
        if not self._action:
            raise BusinessRuleViolationException(rule="Audit log must have an action")
