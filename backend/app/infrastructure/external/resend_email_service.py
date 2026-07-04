"""
Resend Email Service
====================
Production email service using Resend (https://resend.com).
Falls back to StubEmailService behavior when RESEND_API_KEY is not configured.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from backend.app.infrastructure.external.email_service import IEmailService
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class ResendEmailService(IEmailService):
    """Send emails via Resend API."""

    def __init__(self, api_key: str, from_email: str = "noreply@medtrack.app"):
        self._api_key = api_key
        self._from_email = from_email

        try:
            import resend

            resend.api_key = api_key
            self._resend = resend
            logger.info("ResendEmailService initialized", extra={"from_email": from_email})
        except ImportError:
            logger.error(
                "resend package not installed. Run: pip install resend"
            )
            self._resend = None

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> None:
        if not self._resend:
            logger.warning(
                "Resend not available, email not sent",
                extra={"to": to, "subject": subject},
            )
            return

        params: dict = {
            "from": self._from_email,
            "to": [to],
            "subject": subject,
            "text": body,
        }
        if html_body:
            params["html"] = html_body

        try:
            # resend.Emails.send() is synchronous — run in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._resend.Emails.send, params)
            logger.info(
                "Email sent via Resend",
                extra={"to": to, "subject": subject},
            )
        except Exception as e:
            logger.error(
                "Failed to send email via Resend",
                extra={"to": to, "subject": subject, "error": str(e)},
            )
