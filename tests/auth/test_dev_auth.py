"""Tests for development authentication and environment switching."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import resolve_current_user_from_token
from app.auth.dev_jwt import issue_dev_jwt
from app.auth.dev_store import get_dev_user_by_username
from app.config import Settings


def _dev_user() -> object:
    user = get_dev_user_by_username("devuser")
    assert user is not None
    return user


@pytest.mark.asyncio
async def test_dev_login_returns_token(
    app_client: AsyncClient,
) -> None:
    """POST /auth/dev/login returns a bearer token for a seeded user."""
    response = await app_client.post("/auth/dev/login", json={"username": "devuser"})

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["username"] == "devuser"


@pytest.mark.asyncio
async def test_dev_login_rejects_unknown_username(
    app_client: AsyncClient,
) -> None:
    """POST /auth/dev/login returns 401 for an unknown seeded user."""
    response = await app_client.post("/auth/dev/login", json={"username": "missing"})

    assert response.status_code == 401


def test_resolve_current_user_from_valid_dev_token() -> None:
    """A valid development token resolves to the seeded ``UserModel`` instance."""
    settings = Settings(app_env="dev", dev_jwt_secret="test-dev-jwt-secret")
    user = _dev_user()
    token = issue_dev_jwt(user, settings.dev_jwt_secret)

    resolved = resolve_current_user_from_token(token, settings)

    assert resolved.id == 1
    assert resolved.username == "devuser"


@pytest.mark.asyncio
async def test_protected_route_requires_bearer_token(app_client: AsyncClient) -> None:
    """Protected routes reject missing bearer tokens."""
    response = await app_client.get("/api/v1/store/inventory")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_accepts_valid_bearer_token(
    app_client: AsyncClient,
    auth_header: dict[str, str],
) -> None:
    """Protected routes allow requests signed with a valid development token."""
    response = await app_client.get("/api/v1/store/inventory", headers=auth_header)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_route_rejects_expired_token(app_client: AsyncClient) -> None:
    """Protected routes return 401 for expired bearer tokens."""
    user = _dev_user()
    token = issue_dev_jwt(user, "test-dev-jwt-secret", lifetime_seconds=-1)

    response = await app_client.get(
        "/api/v1/store/inventory",
        headers={"Authorization": "Bearer " + token},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_tampered_token(app_client: AsyncClient) -> None:
    """Protected routes return 401 for tampered bearer tokens."""
    user = _dev_user()
    token = issue_dev_jwt(user, "test-dev-jwt-secret")
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    response = await app_client.get(
        "/api/v1/store/inventory",
        headers={"Authorization": "Bearer " + tampered},
    )

    assert response.status_code == 401


def test_environment_switching_uses_supabase_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-dev environments delegate token validation to the Supabase path."""
    settings = Settings(app_env="staging")

    def _fake_validate(token: str, *, settings: Settings) -> dict[str, object]:
        assert token == "supabase-token"
        assert settings.app_env == "staging"
        return {
            "sub": "42",
            "email": "stage@example.com",
            "user_metadata": {
                "username": "stage-user",
                "first_name": "Stage",
                "last_name": "User",
                "phone": "555-9999",
                "user_status": 1,
            },
        }

    monkeypatch.setattr("app.api.deps.validate_supabase_jwt", _fake_validate)

    resolved = resolve_current_user_from_token("supabase-token", settings)

    assert resolved.id == 42
    assert resolved.username == "stage-user"


def test_environment_switching_dev_uses_dev_store() -> None:
    """Dev environment resolution continues to use the in-memory store."""
    settings = Settings(app_env="dev", dev_jwt_secret="test-dev-jwt-secret")
    token = issue_dev_jwt(_dev_user(), settings.dev_jwt_secret)

    resolved = resolve_current_user_from_token(token, settings)

    assert resolved.email == "dev@example.com"
