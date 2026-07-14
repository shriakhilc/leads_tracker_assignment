from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str | None = None


class EmailAdapter(Protocol):
    """Swappable email interface (N5): Mailpit/SMTP locally, SES/SendGrid in prod, console in tests."""

    def send(self, message: EmailMessage) -> None: ...
