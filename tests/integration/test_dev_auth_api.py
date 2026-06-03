"""Integration tests for the development auth API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.auth.dev_jwt import issue_dev_jwt
from app.auth.dev_store import get_dev_user_by_username


def _dev_token(*, lifetime_seconds: int = 3600) -> str:
    user = get_dev_user_by_username("devuser")
    assert user is not None
    return issue_dev_jwt(user, "test-dev-jwt-secret", lifetime_seconds=lifetime_seconds)


@pytest.mark.asyncio
async def test_dev_login_route_returns_seeded_user(app_client: AsyncClient) -> None:
    """POST /api/v1/user/auth returns a bearer token for a seeded user."""
    response = await app_client.post("/api/v1/user/auth", json={"username": "devuser"})

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "devuser"


@pytest.mark.asyncio
async def test_dev_login_route_rejects_unknown_user(app_client: AsyncClient) -> None:
    """POST /api/v1/user/auth returns 401 for unknown development users."""
    response = await app_client.post("/api/v1/user/auth", json={"username": "unknown"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_missing_bearer_token(app_client: AsyncClient) -> None:
    """Protected routes return 401 when the bearer token is missing."""
    response = await app_client.get("/api/v1/store/inventory")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_accepts_valid_bearer_token(
    app_client: AsyncClient,
    auth_header: dict[str, str],
) -> None:
    """Protected routes accept a valid development bearer token."""
    response = await app_client.get("/api/v1/store/inventory", headers=auth_header)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_route_rejects_expired_bearer_token(app_client: AsyncClient) -> None:
    """Protected routes return 401 for expired bearer tokens."""
    response = await app_client.get(
        "/api/v1/store/inventory",
        headers={"Authorization": "Bearer " + _dev_token(lifetime_seconds=-1)},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_tampered_bearer_token(app_client: AsyncClient) -> None:
    """Protected routes return 401 for tampered bearer tokens."""
    token = _dev_token()
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    response = await app_client.get(
        "/api/v1/store/inventory",
        headers={"Authorization": "Bearer " + tampered},
    )

    assert response.status_code == 401
