"""Unit tests for configuration guards (app.core.config)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Fields are passed explicitly and _env_file=None so the real .env never leaks
# into these assertions.
BASE = dict(_env_file=None)


def test_production_with_placeholder_secret_is_refused():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="change-me-in-production", **BASE)


def test_production_with_second_known_placeholder_is_refused():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="dev-secret-change-me", **BASE)


def test_production_with_strong_secret_is_allowed():
    s = Settings(environment="production", jwt_secret="a-very-strong-random-secret", **BASE)
    assert s.environment == "production"
    assert s.jwt_secret == "a-very-strong-random-secret"


def test_local_with_placeholder_secret_is_allowed():
    # The placeholder is fine outside production (local dev / CI convenience).
    s = Settings(environment="local", jwt_secret="change-me-in-production", **BASE)
    assert s.environment == "local"


def test_allowed_resume_types_cover_pdf_doc_docx():
    s = Settings(**BASE)
    assert "application/pdf" in s.allowed_resume_content_types
    assert "application/msword" in s.allowed_resume_content_types
    assert (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in s.allowed_resume_content_types
    )
