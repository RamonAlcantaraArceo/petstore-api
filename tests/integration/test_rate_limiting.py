"""Integration tests for the rate-limiting middleware via the in-memory test client."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import reset_memory_repos
from app.main import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LOW_LIMIT = 3
_BYPASS_KEY = "integration-bypass-key"
_API_KEY = "test-api-key"


@pytest_asyncio.fixture
async def rate_limited_client() -> AsyncIterator[AsyncClient]:
    """Return a test client with a low rate limit (3 req/window) and a known bypass key.

    The fixture sets and then restores the relevant environment variables so it
    does not bleed state into other tests.
    """
    prev = {
        "STORAGE_MODE": os.environ.get("STORAGE_MODE"),
        "API_KEY": os.environ.get("API_KEY"),
        "APP_ENV": os.environ.get("APP_ENV"),
        "DEV_JWT_SECRET": os.environ.get("DEV_JWT_SECRET"),
        "RATE_LIMIT_REQUESTS": os.environ.get("RATE_LIMIT_REQUESTS"),
        "RATE_LIMIT_WINDOW_SECONDS": os.environ.get("RATE_LIMIT_WINDOW_SECONDS"),
        "RATE_LIMIT_BYPASS_KEY": os.environ.get("RATE_LIMIT_BYPASS_KEY"),
        # #SEED_DATASET=mixed_v2
        # "SEED_DATASET": os.environ.get("SEED_DATASET"),
    }

    os.environ["STORAGE_MODE"] = "memory"
    os.environ["API_KEY"] = _API_KEY
    os.environ["APP_ENV"] = "dev"
    os.environ["DEV_JWT_SECRET"] = "test-dev-jwt-secret"
    os.environ["RATE_LIMIT_REQUESTS"] = str(_LOW_LIMIT)
    os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
    os.environ["RATE_LIMIT_BYPASS_KEY"] = _BYPASS_KEY
    # os.environ["SEED_DATASET"] = "mixed_v2"

    from app.dependencies import _cached_settings  # noqa: PLC2701

    _cached_settings.cache_clear()
    reset_memory_repos()

    test_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client

    # Restore previous environment
    for key, val in prev.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val

    _cached_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests — rate limit triggers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_triggers_after_threshold(
    rate_limited_client: AsyncClient,
    api_key_header: dict[str, str],
) -> None:
    """Non-exempt endpoint succeeds up to the threshold; the next request returns 429."""
    headers = api_key_header

    # Requests 1 … _LOW_LIMIT should all succeed (health is exempt, use a real endpoint)
    # Use /api/v1/health which is also exempt to avoid needing actual entities.
    # Instead hit a non-exempt but lightweight endpoint: supply bad key to test 401/429 ordering.
    # Simplest: hit /api/v1/pet without a valid payload — the middleware runs first.
    for _ in range(_LOW_LIMIT):
        response = await rate_limited_client.get("/api/v1/pet/99999", headers=headers)
        # 404 or 200 is fine — as long as it is NOT 429
        assert response.status_code != 429, f"Rate limited too early on request {_ + 1}"

    # The next request should be rate-limited
    response = await rate_limited_client.get("/api/v1/pet/99999", headers=headers)
    assert response.status_code == 429
    data = response.json()
    assert "detail" in data
    assert "retry-after" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_response_body_and_headers(
    rate_limited_client: AsyncClient,
    api_key_header: dict[str, str],
) -> None:
    """Responses expose rate-limit metadata until throttling occurs."""
    headers = api_key_header

    first_response = await rate_limited_client.get("/api/v1/pet/1", headers=headers)
    assert first_response.headers["x-ratelimit-limit"] == str(_LOW_LIMIT)
    assert first_response.headers["x-ratelimit-remaining"] == str(_LOW_LIMIT - 1)
    assert int(first_response.headers["x-ratelimit-reset"]) > 0

    for _ in range(_LOW_LIMIT - 1):
        await rate_limited_client.get("/api/v1/pet/1", headers=headers)

    response = await rate_limited_client.get("/api/v1/pet/1", headers=headers)
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Please retry after the window resets."
    assert int(response.headers["retry-after"]) > 0


# ---------------------------------------------------------------------------
# Tests — bypass mechanism
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bypass_key_allows_unlimited_requests(
    rate_limited_client: AsyncClient,
    api_key_header: dict[str, str],
) -> None:
    """Requests with the correct X-Bypass-Key are never rate-limited."""
    headers = {**api_key_header, "X-Bypass-Key": _BYPASS_KEY}

    for _ in range(_LOW_LIMIT + 5):
        response = await rate_limited_client.get("/api/v1/pet/99999", headers=headers)
        assert response.status_code != 429, "Should not be rate-limited with bypass key"


@pytest.mark.asyncio
async def test_wrong_bypass_key_does_not_bypass_limit(
    rate_limited_client: AsyncClient,
    api_key_header: dict[str, str],
) -> None:
    """Requests with an incorrect X-Bypass-Key are still subject to rate limiting."""
    headers = {**api_key_header, "X-Bypass-Key": "wrong-key"}

    for _ in range(_LOW_LIMIT):
        await rate_limited_client.get("/api/v1/pet/99999", headers=headers)

    response = await rate_limited_client.get("/api/v1/pet/99999", headers=headers)
    assert response.status_code == 429


# ---------------------------------------------------------------------------
# Tests — exempt paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint_is_exempt_from_rate_limiting(
    rate_limited_client: AsyncClient,
) -> None:
    """/health is never rate-limited, even when sending more than the threshold."""
    for _ in range(_LOW_LIMIT + 5):
        response = await rate_limited_client.get("/health")
        assert response.status_code == 200, "Health endpoint should never return 429"


@pytest.mark.asyncio
async def test_openapi_endpoint_is_exempt_from_rate_limiting(
    rate_limited_client: AsyncClient,
) -> None:
    """/openapi.json is never rate-limited."""
    for _ in range(_LOW_LIMIT + 5):
        response = await rate_limited_client.get("/openapi.json")
        assert response.status_code == 200, "/openapi.json should never return 429"


# ---------------------------------------------------------------------------
# Tests — authenticated vs unauthenticated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_requests_are_also_rate_limited(
    rate_limited_client: AsyncClient,
) -> None:
    """Rate limiting applies to unauthenticated requests (keyed by IP)."""
    # No token — auth fails, but rate limiting still counts by client IP.
    for _ in range(_LOW_LIMIT):
        response = await rate_limited_client.delete("/api/v1/pet/1")
        assert response.status_code == 401  # not found, but not rate-limited

    # The (N+1)-th request from the same IP should be rate-limited before auth.
    response = await rate_limited_client.get("/api/v1/pet/1")
    assert response.status_code == 429
