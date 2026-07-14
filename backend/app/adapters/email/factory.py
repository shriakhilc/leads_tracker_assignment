from __future__ import annotations

from functools import lru_cache

from app.adapters.email.base import EmailAdapter
from app.adapters.email.console import ConsoleEmailAdapter
from app.adapters.email.smtp import SmtpEmailAdapter
from app.core.config import settings


@lru_cache
def get_email_adapter() -> EmailAdapter:
    if settings.email_backend == "console":
        return ConsoleEmailAdapter()
    return SmtpEmailAdapter()
