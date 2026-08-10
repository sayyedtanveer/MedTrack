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

    async def execute(self, context: dict) -> None:
        email_service = context.get("email_service")
        if email_service:
            subject = "Registration Received"
            body = f"Hello {self.first_name},\n\nWe have received your registration for tenant {self.tenant_name}. It is currently pending approval.\n\nThank you,\nMedTrack Team"
            html_body = f"<p>Hello <strong>{self.first_name}</strong>,</p><p>We have received your registration for tenant <strong>{self.tenant_name}</strong>. It is currently pending approval.</p><p>Thank you,<br>MedTrack Team</p>"
            
            try:
                await email_service.send_email(
                    to=self.email,
                    subject=subject,
                    body=body,
                    html_body=html_body,
                )
            except Exception as e:
                logger.exception("Failed to send Registration Received email", extra={"email": self.email, "tenant": self.tenant_name})
                raise  # Let BackgroundTaskService handle retries
        else:
            logger.warning("SendRegistrationReceivedEmailTask: no email_service in context")


# ── SendWorkspaceApprovedEmailTask ────────────────────────────────────────────
@dataclass
class SendWorkspaceApprovedEmailTask(IBackgroundTask):
    """Send an approval/welcome email to an admin user once their workspace is active."""
    email: str
    tenant_name: str
    first_name: str

    async def execute(self, context: dict) -> None:
        email_service = context.get("email_service")
        if email_service:
            subject = "Workspace Approved"
            body = f"Hello {self.first_name},\n\nGood news! Your MedTrack workspace for tenant {self.tenant_name} has been approved and is now active.\n\nYou can now log in.\n\nWelcome to MedTrack!"
            html_body = f"<p>Hello <strong>{self.first_name}</strong>,</p><p>Good news! Your MedTrack workspace for tenant <strong>{self.tenant_name}</strong> has been approved and is now active.</p><p>You can now log in.</p><p>Welcome to MedTrack!</p>"
            
            try:
                await email_service.send_email(
                    to=self.email,
                    subject=subject,
                    body=body,
                    html_body=html_body,
                )
            except Exception as e:
                logger.exception("Failed to send Workspace Approved email", extra={"email": self.email, "tenant": self.tenant_name})
                raise  # Let BackgroundTaskService handle retries
        else:
            logger.warning("SendWorkspaceApprovedEmailTask: no email_service in context")


# ── WriteAuditLogTask ─────────────────────────────────────────────────────────
@dataclass
class WriteAuditLogTask(IBackgroundTask):
    """Write an audit log entry in the background (decoupled from request)."""
    action: str
    entity_type: Optional[str] = None
    # NOTE: audit_service is removed from dataclass to keep payload serializable. It's resolved from context.
    # audit_service: Optional[object] = None  # AuditService — injected

    async def execute(self, context: dict) -> None:
        audit_service = context.get("audit_service")
        if audit_service:
            await audit_service.log_action(
                action=self.action,
                entity_type=self.entity_type,
            )
        else:
            logger.warning("WriteAuditLogTask: no audit_service in context")


# ── PublishDomainEventsTask ───────────────────────────────────────────────────
@dataclass
class PublishDomainEventsTask(IBackgroundTask):
    """Fire-and-forget domain event dispatch (fallback if UoW misses events)."""
    events: list
    # NOTE: dispatcher is removed from dataclass to keep payload serializable. It's resolved from context.
    # dispatcher: Optional[object] = None  # EventDispatcher — injected

    async def execute(self, context: dict) -> None:
        dispatcher = context.get("event_dispatcher")
        if not dispatcher:
            return
        for event in self.events:
            await dispatcher.dispatch(event)
