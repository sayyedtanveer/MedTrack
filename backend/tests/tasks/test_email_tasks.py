import pytest
from typing import Optional

from backend.app.infrastructure.external.email_service import IEmailService
from backend.app.infrastructure.tasks.sample_tasks import (
    SendRegistrationReceivedEmailTask,
    SendWorkspaceApprovedEmailTask
)
from backend.app.infrastructure.tasks.background_task_service import BackgroundTaskService

class FakeEmailService(IEmailService):
    def __init__(self):
        self.sent_emails = []

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> None:
        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "body": body,
            "html_body": html_body
        })

@pytest.mark.asyncio
async def test_send_registration_received_email_task():
    # Arrange
    fake_email_service = FakeEmailService()
    task_service = BackgroundTaskService()
    
    # Inject dependencies through task context mechanism
    context = {"email_service": fake_email_service}
    task_service.set_context(context)
    
    task = SendRegistrationReceivedEmailTask(
        email="admin@test.com",
        tenant_name="Test Tenant",
        first_name="Admin"
    )
    
    # Act - Simulate the BackgroundTaskService running it
    await task.execute(context)
    
    # Assert
    assert len(fake_email_service.sent_emails) == 1
    sent = fake_email_service.sent_emails[0]
    assert sent["to"] == "admin@test.com"
    assert sent["subject"] == "Registration Received"
    assert "Admin" in sent["body"]
    assert "Test Tenant" in sent["body"]

@pytest.mark.asyncio
async def test_send_workspace_approved_email_task():
    # Arrange
    fake_email_service = FakeEmailService()
    task_service = BackgroundTaskService()
    
    context = {"email_service": fake_email_service}
    task_service.set_context(context)
    
    task = SendWorkspaceApprovedEmailTask(
        email="admin2@test.com",
        tenant_name="Acme Corp",
        first_name="Jane"
    )
    
    # Act
    await task.execute(context)
    
    # Assert
    assert len(fake_email_service.sent_emails) == 1
    sent = fake_email_service.sent_emails[0]
    assert sent["to"] == "admin2@test.com"
    assert sent["subject"] == "Workspace Approved"
    assert "Jane" in sent["body"]
    assert "Acme Corp" in sent["body"]
