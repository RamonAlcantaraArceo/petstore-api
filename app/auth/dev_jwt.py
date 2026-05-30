"""Development JWT helpers that mimic Supabase claim structure."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.models.user import UserModel

ALGORITHM = "HS256"


class DevJWTError(Exception):
    """Raised when a development JWT is invalid."""


class DevJWTExpiredError(DevJWTError):
    """Raised when a development JWT has expired."""


def _b64url_encode(raw: bytes) -> str:
    """Return a URL-safe base64 string without padding."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    """Decode a URL-safe base64 string with optional padding."""
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}")
    except (ValueError, TypeError) as exc:
        raise DevJWTError("Malformed JWT segment.") from exc


def _json_dumps(payload: dict[str, Any]) -> bytes:
    """Return a stable JSON representation for JWT signing."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def build_dev_claims(
    user: UserModel,
    *,
    lifetime_seconds: int = 3600,
    now: int | None = None,
) -> dict[str, Any]:
    """Build Supabase-shaped claims for a development user."""
    issued_at = int(time.time()) if now is None else now
    return {
        "sub": str(user.id),
        "email": user.email,
        "role": "authenticated",
        "user_metadata": {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "user_status": user.user_status,
        },
        "exp": issued_at + lifetime_seconds,
        "iat": issued_at,
    }


def issue_dev_jwt(
    user: UserModel,
    secret: str,
    *,
    lifetime_seconds: int = 3600,
    now: int | None = None,
) -> str:
    """Create a signed development JWT for the supplied user."""
    header = {"alg": ALGORITHM, "typ": "JWT"}
    claims = build_dev_claims(user, lifetime_seconds=lifetime_seconds, now=now)
    encoded_header = _b64url_encode(_json_dumps(header))
    encoded_claims = _b64url_encode(_json_dumps(claims))
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_claims}.{_b64url_encode(signature)}"


def decode_dev_jwt(token: str, secret: str, *, now: int | None = None) -> dict[str, Any]:
    """Validate and decode a signed development JWT."""
    try:
        encoded_header, encoded_claims, encoded_signature = token.split(".")
    except ValueError as exc:
        raise DevJWTError("Malformed JWT.") from exc

    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    provided_signature = _b64url_decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise DevJWTError("JWT signature verification failed.")

    try:
        header = json.loads(_b64url_decode(encoded_header))
        claims = json.loads(_b64url_decode(encoded_claims))
    except json.JSONDecodeError as exc:
        raise DevJWTError("JWT payload is not valid JSON.") from exc

    if header.get("alg") != ALGORITHM:
        raise DevJWTError("Unsupported JWT algorithm.")

    current_time = int(time.time()) if now is None else now
    expires_at = claims.get("exp")
    if not isinstance(expires_at, int):
        raise DevJWTError("JWT missing integer exp claim.")
    if expires_at <= current_time:
        raise DevJWTExpiredError("JWT has expired.")

    issued_at = claims.get("iat")
    if not isinstance(issued_at, int):
        raise DevJWTError("JWT missing integer iat claim.")

    return claims
