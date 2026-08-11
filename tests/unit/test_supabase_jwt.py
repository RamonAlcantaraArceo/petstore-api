"""Unit tests for Supabase JWT validation."""

from __future__ import annotations

import base64
import time
from collections.abc import Iterator
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)

from app.auth.supabase_jwt import (
    SupabaseJWTError,
    SupabaseJWTExpiredError,
    SupabaseJWTNotConfiguredError,
    _jwks_cache,
    validate_supabase_jwt,
)
from app.config import Settings

_SECRET = "test-supabase-jwt-secret-at-least-32-bytes"
_SUPABASE_URL = "https://project.supabase.co"
_ISSUER = f"{_SUPABASE_URL}/auth/v1"


@pytest.fixture(autouse=True)
def clear_jwks_cache() -> Iterator[None]:
    """Keep the module-level JWKS cache isolated between tests."""
    _jwks_cache.clear()
    yield
    _jwks_cache.clear()


def _valid_claims(*, offset: int = 3600) -> dict[str, Any]:
    """Return valid Supabase JWT claims."""
    now = int(time.time())
    return {
        "sub": "42",
        "aud": "authenticated",
        "iss": _ISSUER,
        "email": "user@example.com",
        "role": "authenticated",
        "exp": now + offset,
        "iat": now,
        "user_metadata": {"username": "sbuser"},
    }


def _settings(secret: str = _SECRET) -> Settings:
    """Return settings configured for both supported JWT algorithms."""
    return Settings(
        app_env="staging",
        supabase_url=_SUPABASE_URL,
        supabase_jwt_secret=secret,
    )


def _b64url_uint(value: int) -> str:
    """Encode an unsigned integer for a JWK."""
    raw = value.to_bytes(32, byteorder="big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _ec_jwk(public_key: EllipticCurvePublicKey, kid: str) -> dict[str, str]:
    """Return a public P-256 key in JWK form."""
    numbers = public_key.public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "alg": "ES256",
        "use": "sig",
        "kid": kid,
        "x": _b64url_uint(numbers.x),
        "y": _b64url_uint(numbers.y),
    }


def _es256_token(
    private_key: EllipticCurvePrivateKey,
    *,
    kid: str,
    claims: dict[str, Any] | None = None,
) -> str:
    """Sign an ES256 token with the supplied key ID."""
    return jwt.encode(
        claims or _valid_claims(),
        private_key,
        algorithm="ES256",
        headers={"kid": kid},
    )


class TestValidateSupabaseJwt:
    """Exercise validation shared by HS256 and ES256 tokens."""

    async def test_valid_hs256_token_returns_claims(self) -> None:
        """A valid HS256 token returns its verified claims."""
        token = jwt.encode(_valid_claims(), _SECRET, algorithm="HS256")

        claims = await validate_supabase_jwt(token, settings=_settings())

        assert claims["sub"] == "42"
        assert claims["email"] == "user@example.com"

    async def test_valid_es256_token_fetches_jwks_asynchronously_and_caches_it(
        self,
    ) -> None:
        """ES256 validation reuses a cached async JWKS response."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        token = _es256_token(private_key, kid="current")
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={"keys": [_ec_jwk(private_key.public_key(), "current")]},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            first = await validate_supabase_jwt(token, settings=_settings(), client=client)
            second = await validate_supabase_jwt(token, settings=_settings(), client=client)

        assert first["sub"] == second["sub"] == "42"
        assert len(requests) == 1
        assert requests[0].url.path == "/auth/v1/.well-known/jwks.json"

    async def test_es256_retries_after_key_rotation(self) -> None:
        """A missing cached key evicts the cache and retries JWKS once."""
        old_key = ec.generate_private_key(ec.SECP256R1())
        new_key = ec.generate_private_key(ec.SECP256R1())
        token = _es256_token(new_key, kid="new")
        calls = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            key = old_key if calls == 1 else new_key
            kid = "old" if calls == 1 else "new"
            return httpx.Response(200, json={"keys": [_ec_jwk(key.public_key(), kid)]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            claims = await validate_supabase_jwt(token, settings=_settings(), client=client)

        assert claims["sub"] == "42"
        assert calls == 2

    @pytest.mark.parametrize(
        ("issuer", "expected"),
        [
            (None, "iss"),
            ("https://other.supabase.co/auth/v1", "issuer"),
        ],
    )
    async def test_rejects_missing_or_invalid_issuer(
        self, issuer: str | None, expected: str
    ) -> None:
        """Tokens must use the configured Supabase Auth issuer."""
        claims = _valid_claims()
        if issuer is None:
            del claims["iss"]
        else:
            claims["iss"] = issuer
        token = jwt.encode(claims, _SECRET, algorithm="HS256")

        with pytest.raises(SupabaseJWTError, match=f"(?i){expected}"):
            await validate_supabase_jwt(token, settings=_settings())

    @pytest.mark.parametrize("claim", ["iat", "sub"])
    async def test_rejects_missing_required_claim(self, claim: str) -> None:
        """Tokens missing a required identity claim are rejected."""
        claims = _valid_claims()
        del claims[claim]
        token = jwt.encode(claims, _SECRET, algorithm="HS256")

        with pytest.raises(SupabaseJWTError, match=claim):
            await validate_supabase_jwt(token, settings=_settings())

    async def test_raises_not_configured_when_secret_empty(self) -> None:
        """Missing HS256 secret raises a configuration error."""
        token = jwt.encode(_valid_claims(), _SECRET, algorithm="HS256")

        with pytest.raises(SupabaseJWTNotConfiguredError):
            await validate_supabase_jwt(token, settings=_settings(secret=""))

    async def test_raises_not_configured_when_url_empty(self) -> None:
        """Missing Supabase URL prevents issuer validation."""
        settings = Settings(app_env="staging", supabase_jwt_secret=_SECRET)
        token = jwt.encode(_valid_claims(), _SECRET, algorithm="HS256")

        with pytest.raises(SupabaseJWTNotConfiguredError):
            await validate_supabase_jwt(token, settings=settings)

    async def test_raises_expired_error_on_expired_token(self) -> None:
        """An expired token raises the dedicated expiration error."""
        token = jwt.encode(_valid_claims(offset=-10), _SECRET, algorithm="HS256")

        with pytest.raises(SupabaseJWTExpiredError):
            await validate_supabase_jwt(token, settings=_settings())

    async def test_raises_error_on_unsupported_algorithm(self) -> None:
        """A token outside the algorithm allowlist is rejected."""
        token = jwt.encode(_valid_claims(), "", algorithm="none")

        with pytest.raises(SupabaseJWTError, match="algorithm"):
            await validate_supabase_jwt(token, settings=_settings())
