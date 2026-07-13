from __future__ import annotations

import logging

from app.adapters.email.base import EmailMessage

logger = logging.getLogger(__name__)


class ConsoleEmailAdapter:
    """Test/CI fake: records + logs messages instead of sending over the network."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)
        logger.info(
            "Email (console)",
            extra={"extra": {"to": message.to, "subject": message.subject}},
        )
