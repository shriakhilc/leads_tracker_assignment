"""Unit tests for the post-commit email side effects (app.services.email_service).

The email adapter, DB session, and repositories are mocked. We assert on which
messages get built and that failures are swallowed (a failed email must never
break the already-committed lead).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.services import email_service
from tests.conftest import make_lead, make_user


class FakeAdapter:
    """Captures sent messages; optionally raises to simulate a broken provider."""

    def __init__(self, raise_on_send=False):
        self.sent = []
        self.raise_on_send = raise_on_send

    def send(self, message):
        if self.raise_on_send:
            raise RuntimeError("smtp down")
        self.sent.append(message)


@pytest.fixture
def wire(monkeypatch):
    """Wire email_service against fakes; returns a helper to configure lead/attorney."""

    def _wire(lead, attorney, adapter=None):
        adapter = adapter or FakeAdapter()
        db = object()  # opaque; repositories are faked so it is never used as a real session

        monkeypatch.setattr(email_service, "get_email_adapter", lambda: adapter)
        monkeypatch.setattr(email_service, "SessionLocal", lambda: _ClosableSession())

        leads_repo = type("R", (), {"__init__": lambda self, db: None, "get": lambda self, _id: lead})
        assignments_repo = type(
            "A",
            (),
            {"__init__": lambda self, db: None, "active_attorney_for_lead": lambda self, _id: attorney},
        )
        monkeypatch.setattr(email_service, "LeadsRepository", leads_repo)
        monkeypatch.setattr(email_service, "AssignmentsRepository", assignments_repo)
        return adapter

    return _wire


class _ClosableSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


# --- format_timestamp -----------------------------------------------------

def test_format_timestamp_naive_is_treated_as_utc():
    dt = datetime(2026, 3, 1, 14, 5)  # naive
    assert email_service.format_timestamp(dt) == "Mar 01, 2026, 14:05 UTC"


def test_format_timestamp_converts_aware_to_utc():
    from datetime import timedelta

    # 09:30 at UTC-5 == 14:30 UTC.
    eastern = timezone(timedelta(hours=-5))
    dt = datetime(2026, 3, 1, 9, 30, tzinfo=eastern)
    assert email_service.format_timestamp(dt) == "Mar 01, 2026, 14:30 UTC"


def test_format_timestamp_renders_midnight_as_00_not_24():
    dt = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert email_service.format_timestamp(dt) == "Jan 01, 2026, 00:00 UTC"


# --- send_submission_emails -----------------------------------------------

def test_sends_prospect_and_attorney_emails(wire):
    lead = make_lead(first_name="Ada", last_name="Lovelace", email="ada@example.com")
    attorney = make_user(email="lawyer@firm.com")
    adapter = wire(lead, attorney)

    email_service.send_submission_emails(lead.id)

    assert len(adapter.sent) == 2
    prospect, notify = adapter.sent
    assert prospect.to == "ada@example.com"
    assert "Ada" in prospect.text_body
    assert notify.to == "lawyer@firm.com"
    assert "Ada Lovelace" in notify.subject
    assert "ada@example.com" in notify.text_body


def test_skips_attorney_email_when_no_active_assignment(wire):
    lead = make_lead(email="ada@example.com")
    adapter = wire(lead, attorney=None)

    email_service.send_submission_emails(lead.id)

    # Prospect still gets confirmed; no attorney notification.
    assert len(adapter.sent) == 1
    assert adapter.sent[0].to == "ada@example.com"


def test_no_emails_when_lead_vanished(wire):
    adapter = wire(lead=None, attorney=None)

    email_service.send_submission_emails(uuid.uuid4())

    assert adapter.sent == []


def test_email_send_failure_is_swallowed(wire):
    lead = make_lead()
    attorney = make_user()
    adapter = wire(lead, attorney, adapter=FakeAdapter(raise_on_send=True))

    # Must not raise, even though every send() throws.
    email_service.send_submission_emails(lead.id)
    assert adapter.sent == []
