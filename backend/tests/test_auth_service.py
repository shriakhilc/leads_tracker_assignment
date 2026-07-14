"""Unit tests for authentication (app.services.auth_service)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.core import security
from app.services.auth_service import AuthService
from tests.conftest import make_user


def _service_with_user(user):
    svc = AuthService(MagicMock(name="Session"))
    svc.users = MagicMock()
    svc.users.get_by_email.return_value = user
    return svc


def test_authenticate_returns_user_on_correct_password():
    user = make_user(hashed_password=security.hash_password("hunter2"))
    svc = _service_with_user(user)

    assert svc.authenticate("attorney@example.com", "hunter2") is user


def test_authenticate_returns_none_on_wrong_password():
    user = make_user(hashed_password=security.hash_password("hunter2"))
    svc = _service_with_user(user)

    assert svc.authenticate("attorney@example.com", "wrong") is None


def test_authenticate_returns_none_for_unknown_email():
    svc = _service_with_user(None)

    assert svc.authenticate("nobody@example.com", "whatever") is None


def test_issue_token_embeds_subject_email_and_role():
    user = make_user(id=uuid.uuid4(), email="lawyer@firm.com", role="attorney")
    svc = _service_with_user(user)

    token = svc.issue_token(user)
    payload = security.decode_access_token(token)

    assert payload["sub"] == str(user.id)
    assert payload["email"] == "lawyer@firm.com"
    assert payload["role"] == "attorney"
