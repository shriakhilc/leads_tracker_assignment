"""Renders templates and dispatches the two submission emails via the EmailAdapter.

These functions are invoked from FastAPI BackgroundTasks *after* the lead + assignment commit
(§8, N4). They construct their own DB session because the request-scoped session is closed by
the time the background task runs.
"""
from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from pathlib import Path

from app.adapters.email import EmailMessage, get_email_adapter
from app.core.config import settings
from app.core.db import SessionLocal
from app.repositories.assignments_repo import AssignmentsRepository
from app.repositories.leads_repo import LeadsRepository

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


@lru_cache
def _load_template(name: str) -> str:
    return (_TEMPLATE_DIR / name).read_text(encoding="utf-8")


def _render(name: str, **context: object) -> str:
    return _load_template(name).format(**context)


def send_submission_emails(lead_id: uuid.UUID) -> None:
    """Post-commit side effect: prospect confirmation + attorney notification.

    Reads the *already-persisted* active assignment; the assignment strategy is never re-run here.
    Failures are logged, never raised — a failed email must not affect the (already committed) lead.
    """
    adapter = get_email_adapter()
    db = SessionLocal()
    try:
        lead = LeadsRepository(db).get(lead_id)
        if lead is None:
            logger.warning("Lead vanished before emailing", extra={"extra": {"lead_id": str(lead_id)}})
            return
        attorney = AssignmentsRepository(db).active_attorney_for_lead(lead_id)

        _safe_send(
            adapter,
            EmailMessage(
                to=lead.email,
                subject="We received your submission",
                text_body=_render("prospect_confirmation.txt", first_name=lead.first_name),
                html_body=_render("prospect_confirmation.html", first_name=lead.first_name),
            ),
        )

        if attorney is not None:
            ctx = dict(
                first_name=lead.first_name,
                last_name=lead.last_name,
                email=lead.email,
                created_at=lead.created_at.isoformat(),
                dashboard_url=settings.dashboard_url,
            )
            _safe_send(
                adapter,
                EmailMessage(
                    to=attorney.email,
                    subject=f"New lead: {lead.first_name} {lead.last_name}",
                    text_body=_render("attorney_notification.txt", **ctx),
                    html_body=_render("attorney_notification.html", **ctx),
                ),
            )
        else:
            logger.error(
                "No active assignment found for lead; attorney email skipped",
                extra={"extra": {"lead_id": str(lead_id)}},
            )
    finally:
        db.close()


def _safe_send(adapter, message: EmailMessage) -> None:
    try:
        adapter.send(message)
    except Exception:  # noqa: BLE001 — email failure must not crash the background task
        logger.exception("Failed to send email", extra={"extra": {"to": message.to}})
