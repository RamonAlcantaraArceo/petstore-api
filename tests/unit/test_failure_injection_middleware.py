"""Unit tests for the failure injection middleware."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import allure
import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.middleware.failure_injection import FailureInjectionMiddleware

pytestmark = [allure.epic("Middleware"), allure.feature("Failure Injection")]


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


def _make_middleware(*, probability: float = 0.5) -> FailureInjectionMiddleware:
    dummy_app: ASGIApp = MagicMock()
    return FailureInjectionMiddleware(dummy_app, probability=probability)


async def _ok_response(_request: Request) -> Response:
    return Response(content="ok", status_code=200)


# ---------------------------------------------------------------------------
# Initialisation — probability clamping
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
    mw = _make_middleware(probability=5.0)
    assert mw._probability == 1.0


@allure.story("Initialisation")
@allure.severity(allure.severity_level.MINOR)
def test_probability_valid_value_preserved() -> None:
    """A probability within [0, 1] is stored unchanged."""
    mw = _make_middleware(probability=0.1)
    assert mw._probability == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# Dispatch — failure injected
# ---------------------------------------------------------------------------


@allure.story("Dispatch")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_failure_injected_returns_error_without_calling_downstream() -> None:
    """When triggered the middleware returns a 5xx response and skips the downstream."""
    mw = _make_middleware(probability=1.0)
    call_next = AsyncMock(return_value=Response(content="downstream", status_code=200))
    request = _make_request()

    with (
        patch("app.middleware.failure_injection.random.random", return_value=0.0),
        patch("app.middleware.failure_injection.random.choice", return_value=500),
    ):
        response = await mw.dispatch(request, call_next)

    call_next.assert_not_awaited()
    assert response.status_code == 500
    body = json.loads(response.body)
    assert "injected" in body["detail"].lower()


@allure.story("Dispatch")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [500, 503, 504])
async def test_failure_injected_returns_correct_status_for_each_error_type(
    status_code: int,
) -> None:
    """Each failure status code (500, 503, 504) is returned with the matching detail."""
    mw = _make_middleware(probability=1.0)
    request = _make_request()

    with (
        patch("app.middleware.failure_injection.random.random", return_value=0.0),
        patch("app.middleware.failure_injection.random.choice", return_value=status_code),
    ):
        response = await mw.dispatch(request, _ok_response)

    assert response.status_code == status_code
    body = json.loads(response.body)
    expected_message = FailureInjectionMiddleware.FAILURE_MESSAGES[status_code]
    assert body["detail"] == expected_message


# ---------------------------------------------------------------------------
# Dispatch — no failure
# ---------------------------------------------------------------------------


@allure.story("Dispatch")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_no_failure_when_random_above_probability() -> None:
    """The downstream is called when random() >= probability."""
    mw = _make_middleware(probability=0.5)
    request = _make_request()

    with patch("app.middleware.failure_injection.random.random", return_value=0.9):
        response = await mw.dispatch(request, _ok_response)

    assert response.status_code == 200


@allure.story("Dispatch")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_no_failure_when_probability_zero() -> None:
    """No failure is ever injected when probability is 0.0."""
    mw = _make_middleware(probability=0.0)
    request = _make_request()

    response = await mw.dispatch(request, _ok_response)

    assert response.status_code == 200
