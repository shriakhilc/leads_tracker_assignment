"""Shared fixtures for the backend unit suite.

These tests are pure unit tests: no Postgres, MinIO, or SMTP. The DB session,
object storage, and email adapter are all replaced with mocks, so the suite runs
anywhere with just `pip install -r requirements-dev.txt`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models import LeadState


@pytest.fixture
def mock_db() -> MagicMock:
    """A stand-in SQLAlchemy Session that records commit/rollback/refresh calls."""
    return MagicMock(name="Session")


def make_lead(**overrides) -> SimpleNamespace:
    """A lightweight Lead-like object (avoids constructing ORM rows / hitting a DB)."""
    defaults = dict(
        id=uuid.uuid4(),
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        resume_key="resumes/abc/resume.pdf",
        resume_filename="resume.pdf",
        resume_content_type="application/pdf",
        state=LeadState.PENDING,
        created_at=datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_user(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        email="attorney@example.com",
        full_name="Attorney Admin",
        role="attorney",
        hashed_password="",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)
