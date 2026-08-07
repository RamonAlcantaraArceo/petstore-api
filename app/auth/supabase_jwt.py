"""Supabase JWT validation for staging and production environments.

Supports both ES256 (JWKS-backed, Supabase default) and HS256 (shared secret,
legacy Supabase projects). Algorithm selection is automatic based on the JWT header.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import httpx
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from jwt.algorithms import ECAlgorithm
from petstore_core.config import Settings

_SUPPORTED_ALGORITHMS = {"ES256", "HS256"}
_JWKS_TTL = 3600  # seconds

# Module-level JWKS cache: url -> (fetched_at, keys_by_kid)
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class SupabaseJWTError(Exception):
    """Raised when a Supabase JWT cannot be validated."""


class SupabaseJWTNotConfiguredError(SupabaseJWTError):
    """Raised when required Supabase settings are missing."""


class SupabaseJWTExpiredError(SupabaseJWTError):
    """Raised when a Supabase JWT has expired."""


def _fetch_jwks(jwks_url: str) -> dict[str, Any]:
    """Fetch JWKS and return a dict keyed by ``kid``, with a 1-hour TTL cache.

    Args:
        jwks_url: Full URL to the JWKS endpoint.

    Returns:
        Dict mapping ``kid`` to JWK dict.

    Raises:
        SupabaseJWTError: If the endpoint is unreachable or the response is malformed.
    """
    cached = _jwks_cache.get(jwks_url)
    if cached and time.time() - cached[0] < _JWKS_TTL:
        return cached[1]

    try:
        response = httpx.get(jwks_url, timeout=10.0)
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise SupabaseJWTError(f"Could not reach JWKS endpoint: {jwks_url}") from exc
    except httpx.HTTPStatusError as exc:
        raise SupabaseJWTError(f"JWKS endpoint returned {exc.response.status_code}") from exc

    try:
        keys_by_kid: dict[str, Any] = {k["kid"]: k for k in response.json()["keys"]}
    except (KeyError, ValueError) as exc:
        raise SupabaseJWTError("Malformed JWKS response.") from exc

    _jwks_cache[jwks_url] = (time.time(), keys_by_kid)
    return keys_by_kid


def _decode_header_unverified(token: str) -> dict[str, Any]:
    """Decode the JWT header without verifying the signature."""
    try:
        encoded_header = token.split(".")[0]
        padding = "=" * (-len(encoded_header) % 4)
        raw = base64.urlsafe_b64decode(f"{encoded_header}{padding}")
        return dict(json.loads(raw))
    except Exception as exc:
        raise SupabaseJWTError("Malformed JWT: could not decode header.") from exc


def validate_supabase_jwt(token: str, *, settings: Settings) -> dict[str, Any]:
    """Validate a Supabase JWT and return its decoded claims.

    Automatically selects the verification strategy based on the JWT header:

    - **ES256**: Fetches the public key from the Supabase JWKS endpoint
      (``{supabase_url}/auth/v1/.well-known/jwks.json``). Requires
      ``SUPABASE_URL`` to be configured.
    - **HS256**: Verifies using the shared ``SUPABASE_JWT_SECRET``.

    JWKS responses are cached in-process for 1 hour to avoid hitting the
    endpoint on every request.

    Args:
        token: Raw JWT bearer token string.
        settings: Application settings.

    Returns:
        Decoded JWT claims as a dictionary.

    Raises:
        SupabaseJWTNotConfiguredError: If required settings are missing.
        SupabaseJWTExpiredError: If the token has expired.
        SupabaseJWTError: If the token is malformed, the signature is invalid,
            or the algorithm is unsupported.
    """
    header = _decode_header_unverified(token)
    alg = header.get("alg", "")

    if alg not in _SUPPORTED_ALGORITHMS:
        raise SupabaseJWTError(
            f"Unsupported JWT algorithm: {alg!r}. Supported: {sorted(_SUPPORTED_ALGORITHMS)}"
        )

    try:
        if alg == "ES256":
            claims = _validate_es256(token, header, settings)
        else:
            claims = _validate_hs256(token, settings)
    except pyjwt.ExpiredSignatureError as exc:
        raise SupabaseJWTExpiredError("JWT has expired.") from exc
    except pyjwt.InvalidTokenError as exc:
        raise SupabaseJWTError(f"JWT validation failed: {exc}") from exc

    return claims


def _validate_es256(token: str, header: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Validate an ES256 JWT via the Supabase JWKS endpoint."""
    if not settings.supabase_url:
        raise SupabaseJWTNotConfiguredError(
            "SUPABASE_URL is required for ES256 JWT validation. "
            "Set the SUPABASE_URL environment variable."
        )

    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    keys_by_kid = _fetch_jwks(jwks_url)

    kid = header.get("kid")
    if not kid or kid not in keys_by_kid:
        # Evict cache and retry once in case keys were rotated
        _jwks_cache.pop(jwks_url, None)
        keys_by_kid = _fetch_jwks(jwks_url)
        if not kid or kid not in keys_by_kid:
            raise SupabaseJWTError(f"No JWKS key found for kid={kid!r}.")

    public_key: EllipticCurvePublicKey = ECAlgorithm.from_jwk(  # type: ignore[assignment]
        json.dumps(keys_by_kid[kid])
    )
    return pyjwt.decode(
        token,
        public_key,
        algorithms=["ES256"],
        audience="authenticated",
        options={"require": ["exp"]},
    )


def _validate_hs256(token: str, settings: Settings) -> dict[str, Any]:
    """Validate an HS256 JWT using the Supabase shared JWT secret."""
    if not settings.supabase_jwt_secret:
        raise SupabaseJWTNotConfiguredError(
            "SUPABASE_JWT_SECRET is required for HS256 JWT validation. "
            "Set the SUPABASE_JWT_SECRET environment variable."
        )

    return pyjwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
        options={"require": ["exp"]},
    )
