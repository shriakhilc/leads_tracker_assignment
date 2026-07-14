from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage as MIMEMessage

from app.adapters.email.base import EmailMessage
from app.core.config import settings

logger = logging.getLogger(__name__)


class SmtpEmailAdapter:
    """Sends via SMTP. Locally points at Mailpit; in prod at SES/SendGrid SMTP."""

    def send(self, message: EmailMessage) -> None:
        mime = MIMEMessage()
        mime["From"] = settings.email_from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text_body)
        if message.html_body:
            mime.add_alternative(message.html_body, subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(mime)

        logger.info("Email sent", extra={"extra": {"to": message.to, "subject": message.subject}})
