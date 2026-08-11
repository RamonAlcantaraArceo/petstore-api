"""Unit tests for Supabase Auth REST helpers."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
from fastapi import HTTPException

from app.auth.supabase_auth import (
    SupabaseAuthNotConfiguredError,
    supabase_delete_user,
    supabase_get_user_by_email,
    supabase_sign_in,
    supabase_sign_out,
    supabase_sign_up,
    supabase_update_user,
)
from app.config import Settings

_AsyncClient = httpx.AsyncClient


def _settings() -> Settings:
    """Return fully configured Supabase settings."""
    return Settings(
        app_env="staging",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="public-key",
        supabase_service_role_key="admin-key",
    )


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    """Route helper HTTP calls through an in-process mock transport."""
    transport = httpx.MockTransport(handler)

    def client_factory(*, timeout: float) -> httpx.AsyncClient:
        assert timeout == 10.0
        return _AsyncClient(transport=transport)

    monkeypatch.setattr("app.auth.supabase_auth.httpx.AsyncClient", client_factory)


async def test_sign_in_sends_password_grant_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sign-in sends email credentials and the configured public key."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"access_token": "token", "token_type": "bearer"})

    _install_transport(monkeypatch, handler)

    result = await supabase_sign_in("user@example.com", "password", settings=_settings())

    assert result["access_token"] == "token"
    assert requests[0].url.path == "/auth/v1/token"
    assert requests[0].url.params["grant_type"] == "password"
    assert requests[0].headers["apikey"] == "public-key"
    assert json.loads(requests[0].content) == {
        "email": "user@example.com",
        "password": "password",
    }


@pytest.mark.parametrize(
    ("status_code", "expected_status", "expected_detail"),
    [
        (400, 401, "Invalid credentials."),
        (500, 502, "unexpected error (500)"),
    ],
)
async def test_sign_in_maps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_status: int,
    expected_detail: str,
) -> None:
    """Sign-in exposes credential failures distinctly from provider failures."""
    _install_transport(
        monkeypatch,
        lambda _request: httpx.Response(status_code, json={"message": "failure"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await supabase_sign_in("user@example.com", "password", settings=_settings())

    assert exc_info.value.status_code == expected_status
    assert expected_detail in str(exc_info.value.detail)


async def test_sign_in_surfaces_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sign-in maps transport failures to service unavailable."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    _install_transport(monkeypatch, handler)

    with pytest.raises(HTTPException) as exc_info:
        await supabase_sign_in("user@example.com", "password", settings=_settings())

    assert exc_info.value.status_code == 503


async def test_sign_up_sends_metadata_and_returns_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sign-up sends profile metadata in Supabase's data field."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"id": "user-id", "identities": [{"id": "identity-id"}]},
        )

    _install_transport(monkeypatch, handler)

    result = await supabase_sign_up(
        "user@example.com",
        "password",
        metadata={"username": "user"},
        settings=_settings(),
    )

    assert result["id"] == "user-id"
    assert json.loads(requests[0].content)["data"] == {"username": "user"}


@pytest.mark.parametrize(
    ("status_code", "payload", "expected_status"),
    [
        (400, {"msg": "bad signup"}, 400),
        (422, {"message": "weak password"}, 422),
        (200, {"id": "existing", "identities": []}, 409),
        (503, {"message": "provider down"}, 502),
    ],
)
async def test_sign_up_maps_provider_responses(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    payload: dict[str, object],
    expected_status: int,
) -> None:
    """Sign-up distinguishes invalid, duplicate, and provider-error responses."""
    _install_transport(
        monkeypatch,
        lambda _request: httpx.Response(status_code, json=payload),
    )

    with pytest.raises(HTTPException) as exc_info:
        await supabase_sign_up("user@example.com", "password", settings=_settings())

    assert exc_info.value.status_code == expected_status


async def test_update_user_sends_only_requested_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profile updates include the bearer token and supplied fields."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "user-id", "email": "new@example.com"})

    _install_transport(monkeypatch, handler)

    result = await supabase_update_user(
        "access-token",
        email="new@example.com",
        phone="555-0100",
        metadata={"first_name": "New"},
        settings=_settings(),
    )

    assert result["email"] == "new@example.com"
    assert requests[0].method == "PUT"
    assert requests[0].headers["authorization"] == "Bearer access-token"
    assert json.loads(requests[0].content) == {
        "email": "new@example.com",
        "phone": "555-0100",
        "data": {"first_name": "New"},
    }


@pytest.mark.parametrize(("status_code", "expected_status"), [(422, 422), (500, 502)])
async def test_update_user_maps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_status: int,
) -> None:
    """Profile updates preserve validation errors and map provider failures."""
    _install_transport(
        monkeypatch,
        lambda _request: httpx.Response(status_code, json={"message": "invalid"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await supabase_update_user("access-token", email="bad", settings=_settings())

    assert exc_info.value.status_code == expected_status


async def test_delete_user_uses_admin_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """User deletion calls the admin endpoint with the server-side key."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    _install_transport(monkeypatch, handler)

    await supabase_delete_user("user-id", settings=_settings())

    assert requests[0].url.path == "/auth/v1/admin/users/user-id"
    assert requests[0].headers["apikey"] == "admin-key"
    assert requests[0].headers["authorization"] == "Bearer admin-key"


@pytest.mark.parametrize(("status_code", "expected_status"), [(404, 404), (500, 502)])
async def test_delete_user_maps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_status: int,
) -> None:
    """User deletion distinguishes missing users from provider failures."""
    _install_transport(monkeypatch, lambda _request: httpx.Response(status_code))

    with pytest.raises(HTTPException) as exc_info:
        await supabase_delete_user("user-id", settings=_settings())

    assert exc_info.value.status_code == expected_status


async def test_get_user_by_email_scans_paginated_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin lookup continues through a full page and normalizes email case."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            users = [
                {"id": f"id-{index}", "email": f"user{index}@example.com"} for index in range(200)
            ]
        else:
            users = [{"id": "target-id", "email": " Target@Example.com "}]
        return httpx.Response(200, json={"users": users})

    _install_transport(monkeypatch, handler)

    result = await supabase_get_user_by_email("target@example.com", settings=_settings())

    assert result["id"] == "target-id"
    assert calls == 2


async def test_get_user_by_email_returns_not_found_after_last_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin lookup returns 404 after a short page has no matching user."""
    _install_transport(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=[{"id": "other-id", "email": "other@example.com"}],
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await supabase_get_user_by_email("missing@example.com", settings=_settings())

    assert exc_info.value.status_code == 404


async def test_get_user_by_email_maps_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin lookup surfaces provider failures instead of returning not found."""
    _install_transport(monkeypatch, lambda _request: httpx.Response(500))

    with pytest.raises(HTTPException) as exc_info:
        await supabase_get_user_by_email("user@example.com", settings=_settings())

    assert exc_info.value.status_code == 502


async def test_sign_out_sends_session_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sign-out calls the logout endpoint with the user's bearer token."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    _install_transport(monkeypatch, handler)

    await supabase_sign_out("access-token", settings=_settings())

    assert requests[0].url.path == "/auth/v1/logout"
    assert requests[0].headers["authorization"] == "Bearer access-token"


@pytest.mark.parametrize(
    "helper",
    [
        lambda settings: supabase_sign_in("user@example.com", "password", settings=settings),
        lambda settings: supabase_sign_up("user@example.com", "password", settings=settings),
        lambda settings: supabase_update_user("token", settings=settings),
        lambda settings: supabase_delete_user("user-id", settings=settings),
        lambda settings: supabase_get_user_by_email("user@example.com", settings=settings),
        lambda settings: supabase_sign_out("token", settings=settings),
    ],
)
async def test_helpers_reject_missing_configuration(
    helper: Callable[[Settings], object],
) -> None:
    """Every Supabase helper fails explicitly when its required keys are absent."""
    with pytest.raises(SupabaseAuthNotConfiguredError):
        await helper(Settings(app_env="staging"))  # type: ignore[misc]
