"""Unit tests for the rate-limiting middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import allure
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.middleware.rate_limit import BYPASS_HEADER, RateLimitMiddleware, _get_client_key

pytestmark = [allure.epic("Middleware"), allure.feature("Rate Limiting")]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    *,
    path: str = "/api/v1/pet",
    api_key: str = "test-key",
    bypass_key: str = "",
    client_ip: str = "127.0.0.1",
) -> Request:
    """Build a minimal Starlette Request for unit tests."""
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            *([(b"x-api-key", api_key.encode())] if api_key else []),
            *([(BYPASS_HEADER.lower().encode(), bypass_key.encode())] if bypass_key else []),
        ],
        "client": (client_ip, 12345),
    }
    return Request(scope)  # type: ignore[arg-type]


def _make_middleware(
    *,
    max_requests: int = 5,
    window_seconds: int = 60,
    bypass_key: str = "secret",
) -> RateLimitMiddleware:
    """Construct a RateLimitMiddleware wrapping a no-op ASGI app."""
    dummy_app: ASGIApp = MagicMock()
    return RateLimitMiddleware(
        dummy_app,
        max_requests=max_requests,
        window_seconds=window_seconds,
        bypass_key=bypass_key,
    )


async def _ok_response(_request: Request) -> Response:
    return Response(content="ok", status_code=200)


# ---------------------------------------------------------------------------
# _get_client_key
# ---------------------------------------------------------------------------


@allure.story("Client Key Resolution")
@allure.severity(allure.severity_level.MINOR)
def test_get_client_key_uses_api_key() -> None:
    """_get_client_key returns an API-prefixed key when X-API-Key is present."""
    request = _make_request(api_key="my-key", client_ip="10.0.0.1")
    assert _get_client_key(request) == "api:my-key"


@allure.story("Client Key Resolution")
@allure.severity(allure.severity_level.MINOR)
def test_get_client_key_falls_back_to_ip() -> None:
    """_get_client_key returns an IP-prefixed key when X-API-Key is absent."""
    request = _make_request(api_key="", client_ip="10.0.0.2")
    assert _get_client_key(request) == "ip:10.0.0.2"


@allure.story("Client Key Resolution")
@allure.severity(allure.severity_level.MINOR)
def test_get_client_key_uses_forwarded_for() -> None:
    """_get_client_key prefers the first IP in X-Forwarded-For over the direct client."""
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/pet",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"x-forwarded-for", b"1.2.3.4, 5.6.7.8"),
        ],
        "client": ("10.0.0.1", 9000),
    }
    request = Request(scope)  # type: ignore[arg-type]
    assert _get_client_key(request) == "ip:1.2.3.4"


# ---------------------------------------------------------------------------
# dispatch — exempt paths
# ---------------------------------------------------------------------------


@allure.story("Exempt Paths")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_health_path_is_exempt() -> None:
    """Requests to /health bypass rate limiting regardless of count."""
    middleware = _make_middleware(max_requests=0)  # limit of 0 → everything should be blocked
    request = _make_request(path="/health")

    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    call_next.assert_awaited_once()


@allure.story("Exempt Paths")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_openapi_path_is_exempt() -> None:
    """/openapi.json is exempt from rate limiting."""
    middleware = _make_middleware(max_requests=0)
    request = _make_request(path="/openapi.json")

    call_next = AsyncMock(return_value=Response(content="{}", status_code=200))
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# dispatch — bypass header
# ---------------------------------------------------------------------------


@allure.story("Bypass Mechanism")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_bypass_key_skips_rate_limit() -> None:
    """A valid X-Bypass-Key header allows unlimited requests."""
    middleware = _make_middleware(max_requests=1, bypass_key="secret")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    for _ in range(10):
        request = _make_request(bypass_key="secret")
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    assert call_next.await_count == 10


@allure.story("Bypass Mechanism")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_wrong_bypass_key_does_not_bypass() -> None:
    """An incorrect X-Bypass-Key value does not bypass rate limiting."""
    middleware = _make_middleware(max_requests=1, bypass_key="secret")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    # First request passes
    response = await middleware.dispatch(_make_request(bypass_key="wrong"), call_next)
    assert response.status_code == 200

    # Second request should be rate-limited
    response = await middleware.dispatch(_make_request(bypass_key="wrong"), call_next)
    assert response.status_code == 429


@allure.story("Bypass Mechanism")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_empty_bypass_key_config_disables_bypass() -> None:
    """When bypass_key is empty the bypass mechanism is disabled."""
    middleware = _make_middleware(max_requests=1, bypass_key="")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    # Even when the header is sent it should not bypass
    response = await middleware.dispatch(_make_request(bypass_key="anything"), call_next)
    assert response.status_code == 200  # first request

    response = await middleware.dispatch(_make_request(bypass_key="anything"), call_next)
    assert response.status_code == 429


# ---------------------------------------------------------------------------
# dispatch — rate limit enforcement
# ---------------------------------------------------------------------------


@allure.story("Rate Limit Enforcement")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_requests_within_limit_pass() -> None:
    """Requests up to max_requests in the window all receive 200."""
    middleware = _make_middleware(max_requests=3, bypass_key="")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    for _ in range(3):
        response = await middleware.dispatch(_make_request(), call_next)
        assert response.status_code == 200


@allure.story("Rate Limit Enforcement")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_exceeding_limit_returns_429() -> None:
    """The (max_requests + 1)-th request in the window returns 429."""
    middleware = _make_middleware(max_requests=3, bypass_key="")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    for _ in range(3):
        await middleware.dispatch(_make_request(), call_next)

    response = await middleware.dispatch(_make_request(), call_next)
    assert response.status_code == 429
    assert isinstance(response, JSONResponse)


@allure.story("Rate Limit Enforcement")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_429_response_has_retry_after_header() -> None:
    """429 response includes a Retry-After header."""
    middleware = _make_middleware(max_requests=1, bypass_key="")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    await middleware.dispatch(_make_request(), call_next)
    response = await middleware.dispatch(_make_request(), call_next)

    assert response.status_code == 429
    assert "retry-after" in response.headers


@allure.story("Rate Limit Enforcement")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_different_clients_have_separate_counters() -> None:
    """Each API key maintains its own request counter."""
    middleware = _make_middleware(max_requests=1, bypass_key="")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    # First client exhausts its quota
    await middleware.dispatch(_make_request(api_key="key-A"), call_next)
    resp_a = await middleware.dispatch(_make_request(api_key="key-A"), call_next)
    assert resp_a.status_code == 429

    # Second client still has its own fresh quota
    resp_b = await middleware.dispatch(_make_request(api_key="key-B"), call_next)
    assert resp_b.status_code == 200


# ---------------------------------------------------------------------------
# Window reset
# ---------------------------------------------------------------------------


@allure.story("Window Reset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_counter_resets_after_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """After the window expires the counter resets and requests are allowed again."""
    import app.middleware.rate_limit as rl_module

    fake_time = [0.0]

    def _fake_time() -> float:
        return fake_time[0]

    monkeypatch.setattr(rl_module, "time", type("_T", (), {"time": staticmethod(_fake_time)})())

    middleware = _make_middleware(max_requests=1, window_seconds=60, bypass_key="")
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    await middleware.dispatch(_make_request(), call_next)
    resp = await middleware.dispatch(_make_request(), call_next)
    assert resp.status_code == 429

    # Advance time beyond the window
    fake_time[0] = 61.0

    resp_after = await middleware.dispatch(_make_request(), call_next)
    assert resp_after.status_code == 200
