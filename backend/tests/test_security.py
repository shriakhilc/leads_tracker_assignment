"""Unit tests for password hashing and JWT encode/decode (app.core.security)."""
from __future__ import annotations

import uuid

import jwt
import pytest

from app.core import security
from app.core.config import settings


def test_hash_password_is_not_plaintext_and_verifies():
    hashed = security.hash_password("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert security.verify_password("s3cret-pw", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = security.hash_password("correct horse")
    assert security.verify_password("battery staple", hashed) is False


def test_hash_password_is_salted_unique_per_call():
    # Two hashes of the same password differ (random salt) but both still verify.
    a = security.hash_password("same-pw")
    b = security.hash_password("same-pw")
    assert a != b
    assert security.verify_password("same-pw", a)
    assert security.verify_password("same-pw", b)


def test_access_token_round_trips_subject_and_extra_claims():
    subject = str(uuid.uuid4())
    token = security.create_access_token(subject, extra_claims={"email": "a@b.com", "role": "attorney"})

    payload = security.decode_access_token(token)

    assert payload["sub"] == subject
    assert payload["email"] == "a@b.com"
    assert payload["role"] == "attorney"
    assert "exp" in payload and "iat" in payload


def test_decode_rejects_token_signed_with_a_different_secret():
    forged = jwt.encode({"sub": "x"}, "not-the-real-secret", algorithm=settings.jwt_algorithm)
    with pytest.raises(jwt.InvalidSignatureError):
        security.decode_access_token(forged)


def test_decode_rejects_expired_token(monkeypatch):
    # Force the token to be minted already-expired.
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    expired = security.create_access_token("subject")
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(expired)


def test_decode_rejects_garbage_token():
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token("not-a-jwt")
