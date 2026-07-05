"""
Resend Email Service
====================
Production-ready email service using Resend (https://resend.com).

Configuration:
    RESEND_API_KEY
    RESEND_FROM_EMAIL

Development:
    RESEND_FROM_EMAIL = "MedTrack <onboarding@resend.dev>"

Production:
    RESEND_FROM_EMAIL = "MedTrack <noreply@medtrack.app>"
"""

from __future__ import annotations

import asyncio
from typing import Optional

from backend.app.infrastructure.external.email_service import IEmailService
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class ResendEmailService(IEmailService):
    """Email service implementation using Resend."""

    def __init__(
        self,
        api_key: str,
        from_email: str,
    ) -> None:
        self._api_key = api_key
        self._from_email = from_email

        if not api_key:
            raise ValueError("RESEND_API_KEY is missing.")

        try:
            import resend

            resend.api_key = api_key
            self._resend = resend

            logger.info(
                "ResendEmailService initialized",
                extra={
                    "from_email": from_email,
                },
            )

        except ImportError as ex:
            logger.exception(
                "Resend package is not installed. Install it using: pip install resend"
            )
            raise ex

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> None:
        """
        Send an email using Resend.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Plain text body.
            html_body: Optional HTML body.
        """

        import resend

        params: resend.Emails.SendParams = {
            "from": self._from_email,
            "to": [to],
            "subject": subject,
            "text": body,
        }

        if html_body:
            params["html"] = html_body

        try:
            response = await asyncio.to_thread(
                self._resend.Emails.send,
                params,
            )

            logger.info(
                "Email sent successfully",
                extra={
                    "to": to,
                    "subject": subject,
                    "response": str(response),
                },
            )

        except Exception as ex:
            logger.exception(
                "Failed to send email via Resend",
                extra={
                    "to": to,
                    "subject": subject,
                },
            )
            raise ex
