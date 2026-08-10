from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.app.infrastructure.tasks.task_interface import IBackgroundTask
from backend.app.infrastructure.context.request_context import set_request_context, clear_request_context


class AuditLogTask(IBackgroundTask):
    """
    Background task to write an audit log entry.
    Captures the context variables at creation time and restores them in the
    background worker before invoking the AuditService.
    """

    def __init__(
        self,
        tenant_id: str | None,
        user_id: str | None,
        ip_address: str | None,
        correlation_id: str | None,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.ip_address = ip_address
        self.correlation_id = correlation_id
        
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.extra = extra

    async def execute(self, context: dict) -> None:
        # Restore context variables for the background task execution
        set_request_context(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address=self.ip_address,
            correlation_id=self.correlation_id,
        )
        
        try:
            audit_service = context["audit_service"]
            await audit_service.log_action(
                action=self.action,
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                extra=self.extra,
            )
        finally:
            # Clean up context vars for the worker (especially important if using a thread/async pool)
            clear_request_context()
