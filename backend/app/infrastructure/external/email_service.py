from __future__ import annotations

from abc import abstractmethod
from typing import Optional

from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class IEmailService:
    """Abstract email service — swap stub for SendGrid/SES in production."""

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> None: ...


class StubEmailService(IEmailService):
    """Phase 0 stub — logs emails instead of sending."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> None:
        logger.info(
            "Email stub: would send email",
            extra={"to": to, "subject": subject},
        )
