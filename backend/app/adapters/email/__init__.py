from app.adapters.email.base import EmailAdapter, EmailMessage
from app.adapters.email.factory import get_email_adapter

__all__ = ["EmailAdapter", "EmailMessage", "get_email_adapter"]
