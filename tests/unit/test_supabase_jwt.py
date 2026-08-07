"""Unit tests for Supabase JWT validation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest

from app.auth.supabase_jwt import (
    SupabaseJWTError,
    SupabaseJWTExpiredError,
    SupabaseJWTNotConfiguredError,
    validate_supabase_jwt,
)
from app.config import Settings

_SECRET = "test-supabase-jwt-secret"


def _make_jwt(
    claims: dict,
    secret: str = _SECRET,
    alg: str = "HS256",
) -> str:
    """Build a signed HS256 JWT for testing."""

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    header = {"alg": alg, "typ": "JWT"}
    encoded_header = b64url(json.dumps(header, separators=(",", ":")).encode())
    encoded_claims = b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_claims}.{b64url(signature)}"


def _valid_claims(*, offset: int = 3600) -> dict:
    now = int(time.time())
    return {
        "sub": "42",
        "aud": "authenticated",
        "email": "user@example.com",
        "role": "authenticated",
        "exp": now + offset,
        "iat": now,
        "user_metadata": {"username": "sbuser"},
    }


def _settings(secret: str = _SECRET) -> Settings:
    return Settings(app_env="staging", supabase_jwt_secret=secret)


class TestValidateSupabaseJwt:
    def test_valid_token_returns_claims(self) -> None:
        """A well-formed, unexpired token returns its decoded claims."""
        token = _make_jwt(_valid_claims())
        claims = validate_supabase_jwt(token, settings=_settings())
        assert claims["sub"] == "42"
        assert claims["email"] == "user@example.com"

    def test_raises_not_configured_when_secret_empty(self) -> None:
        """Missing secret raises SupabaseJWTNotConfiguredError."""
        settings = Settings(app_env="staging", supabase_jwt_secret="")
        token = _make_jwt(_valid_claims())
        with pytest.raises(SupabaseJWTNotConfiguredError):
            validate_supabase_jwt(token, settings=settings)

    def test_raises_error_on_wrong_secret(self) -> None:
        """A token signed with the wrong secret fails verification."""
        token = _make_jwt(_valid_claims(), secret="wrong-secret")
        with pytest.raises(SupabaseJWTError, match="(?i)signature"):
            validate_supabase_jwt(token, settings=_settings())

    def test_raises_expired_error_on_expired_token(self) -> None:
        """An expired token raises SupabaseJWTExpiredError."""
        claims = _valid_claims(offset=-10)  # expired 10 seconds ago
        token = _make_jwt(claims)
        with pytest.raises(SupabaseJWTExpiredError):
            validate_supabase_jwt(token, settings=_settings())

    def test_raises_error_on_malformed_token(self) -> None:
        """A token without three segments raises SupabaseJWTError."""
        with pytest.raises(SupabaseJWTError, match="Malformed"):
            validate_supabase_jwt("not.a.valid.jwt.token", settings=_settings())

    def test_raises_error_on_tampered_payload(self) -> None:
        """Changing the payload after signing fails verification."""
        token = _make_jwt(_valid_claims())
        header, _, sig = token.split(".")
        # Build a forged payload
        forged_claims = _valid_claims()
        forged_claims["sub"] = "999"
        forged_encoded = (
            base64.urlsafe_b64encode(json.dumps(forged_claims, separators=(",", ":")).encode())
            .rstrip(b"=")
            .decode()
        )
        forged_token = f"{header}.{forged_encoded}.{sig}"
        with pytest.raises(SupabaseJWTError, match="(?i)signature"):
            validate_supabase_jwt(forged_token, settings=_settings())

    def test_raises_error_on_unsupported_algorithm(self) -> None:
        """A token with an algorithm other than HS256 is rejected."""
        token = _make_jwt(_valid_claims(), alg="none")
        with pytest.raises(SupabaseJWTError, match="algorithm"):
            validate_supabase_jwt(token, settings=_settings())

    def test_raises_error_on_missing_exp(self) -> None:
        """A token without an 'exp' claim is rejected."""
        claims = _valid_claims()
        del claims["exp"]
        token = _make_jwt(claims)
        with pytest.raises(SupabaseJWTError, match="exp"):
            validate_supabase_jwt(token, settings=_settings())
