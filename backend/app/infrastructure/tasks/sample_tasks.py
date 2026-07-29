from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.app.infrastructure.tasks.task_interface import IBackgroundTask
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


# ── SendRegistrationReceivedEmailTask ──────────────────────────────────────────
@dataclass
class SendRegistrationReceivedEmailTask(IBackgroundTask):
    """Send an acknowledgment email to a newly registered admin user (pending approval)."""
    email: str
    tenant_name: str
    first_name: str

    async def execute(self) -> None:
        logger.info(
            "Sending registration received email (stub)",
            extra={"email": self.email, "tenant": self.tenant_name},
        )


# ── SendWorkspaceApprovedEmailTask ────────────────────────────────────────────
@dataclass
class SendWorkspaceApprovedEmailTask(IBackgroundTask):
    """Send an approval/welcome email to an admin user once their workspace is active."""
    email: str
    tenant_name: str
    first_name: str

    async def execute(self) -> None:
        logger.info(
            "Sending workspace approved email (stub)",
            extra={"email": self.email, "tenant": self.tenant_name},
        )


# ── WriteAuditLogTask ─────────────────────────────────────────────────────────
@dataclass
class WriteAuditLogTask(IBackgroundTask):
    """Write an audit log entry in the background (decoupled from request)."""
    action: str
    entity_type: Optional[str] = None
    audit_service: Optional[object] = None  # AuditService — injected

    async def execute(self) -> None:
        if self.audit_service:
            await self.audit_service.log_action(
                action=self.action,
                entity_type=self.entity_type,
            )
        else:
            logger.warning("WriteAuditLogTask: no audit_service injected")


# ── PublishDomainEventsTask ───────────────────────────────────────────────────
@dataclass
class PublishDomainEventsTask(IBackgroundTask):
    """Fire-and-forget domain event dispatch (fallback if UoW misses events)."""
    events: list
    dispatcher: Optional[object] = None  # EventDispatcher — injected

    async def execute(self) -> None:
        if not self.dispatcher:
            return
        for event in self.events:
            await self.dispatcher.dispatch(event)
