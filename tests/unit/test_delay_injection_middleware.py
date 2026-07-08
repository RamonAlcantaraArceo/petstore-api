"""Unit tests for the delay injection middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import allure
import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.middleware.delay_injection import DelayInjectionMiddleware

pytestmark = [allure.epic("Middleware"), allure.feature("Delay Injection")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(path: str = "/api/v1/pet") -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)  # type: ignore[arg-type]


def _make_middleware(
    *, probability: float = 0.5, max_delay_seconds: float = 2.0
) -> DelayInjectionMiddleware:
    dummy_app: ASGIApp = MagicMock()
    return DelayInjectionMiddleware(
        dummy_app, probability=probability, max_delay_seconds=max_delay_seconds
    )


async def _ok_response(_request: Request) -> Response:
    return Response(content="ok", status_code=200)


# ---------------------------------------------------------------------------
# Initialisation — probability and max_delay_seconds clamping
# ---------------------------------------------------------------------------


@allure.story("Initialisation")
@allure.severity(allure.severity_level.MINOR)
def test_probability_clamped_below_zero() -> None:
    """Probability below 0.0 is clamped to 0.0."""
    mw = _make_middleware(probability=-0.5)
    assert mw._probability == 0.0


@allure.story("Initialisation")
@allure.severity(allure.severity_level.MINOR)
def test_probability_clamped_above_one() -> None:
    """Probability above 1.0 is clamped to 1.0."""
    mw = _make_middleware(probability=2.5)
    assert mw._probability == 1.0


@allure.story("Initialisation")
@allure.severity(allure.severity_level.MINOR)
def test_probability_valid_value_preserved() -> None:
    """A probability within [0, 1] is stored unchanged."""
    mw = _make_middleware(probability=0.3)
    assert mw._probability == pytest.approx(0.3)


@allure.story("Initialisation")
@allure.severity(allure.severity_level.MINOR)
def test_max_delay_seconds_clamped_below_zero() -> None:
    """max_delay_seconds below 0.0 is clamped to 0.0."""
    mw = _make_middleware(max_delay_seconds=-1.0)
    assert mw._max_delay_seconds == 0.0


@allure.story("Initialisation")
@allure.severity(allure.severity_level.MINOR)
def test_max_delay_seconds_valid_value_preserved() -> None:
    """A positive max_delay_seconds is stored unchanged."""
    mw = _make_middleware(max_delay_seconds=3.5)
    assert mw._max_delay_seconds == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Dispatch — delay injected
# ---------------------------------------------------------------------------


@allure.story("Dispatch")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_delay_injected_calls_asyncio_sleep() -> None:
    """asyncio.sleep is called with a value <= max_delay_seconds when triggered."""
    mw = _make_middleware(probability=1.0, max_delay_seconds=1.0)
    request = _make_request()

    with (
        patch("app.middleware.delay_injection.random.random", return_value=0.0),
        patch("app.middleware.delay_injection.random.uniform", return_value=0.42),
        patch("app.middleware.delay_injection.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        response = await mw.dispatch(request, _ok_response)

    mock_sleep.assert_awaited_once_with(0.42)
    assert response.status_code == 200


@allure.story("Dispatch")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_delay_injected_still_forwards_request() -> None:
    """The downstream handler is called even when delay is injected."""
    mw = _make_middleware(probability=1.0, max_delay_seconds=0.1)
    call_next = AsyncMock(return_value=Response(content="downstream", status_code=200))
    request = _make_request()

    with (
        patch("app.middleware.delay_injection.random.random", return_value=0.0),
        patch("app.middleware.delay_injection.random.uniform", return_value=0.05),
        patch("app.middleware.delay_injection.asyncio.sleep", new_callable=AsyncMock),
    ):
        response = await mw.dispatch(request, call_next)

    call_next.assert_awaited_once()
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Dispatch — no delay
# ---------------------------------------------------------------------------


@allure.story("Dispatch")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_no_delay_when_random_above_probability() -> None:
    """asyncio.sleep is not called when random() >= probability."""
    mw = _make_middleware(probability=0.5)
    request = _make_request()

    with patch(
        "app.middleware.delay_injection.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        with patch("app.middleware.delay_injection.random.random", return_value=0.9):
            response = await mw.dispatch(request, _ok_response)

    mock_sleep.assert_not_awaited()
    assert response.status_code == 200


@allure.story("Dispatch")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_no_delay_when_probability_zero() -> None:
    """No delay is ever injected when probability is 0.0."""
    mw = _make_middleware(probability=0.0)
    request = _make_request()

    with patch(
        "app.middleware.delay_injection.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        response = await mw.dispatch(request, _ok_response)

    mock_sleep.assert_not_awaited()
    assert response.status_code == 200
