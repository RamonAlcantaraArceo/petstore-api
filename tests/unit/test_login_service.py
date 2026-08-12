"""Unit tests for the shared user login service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from petstore_core.config import Settings
from petstore_core.models.user import UserModel
from petstore_core.services.user import UserService

from app.auth.dev_store import reset_dev_users, upsert_dev_user
from app.auth.login import perform_login


async def test_supabase_login_uses_password_grant_and_validates_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supabase login validates the password-grant access token before returning it."""
    sign_in = AsyncMock(return_value={"access_token": "signed-token", "token_type": "bearer"})
    validate = AsyncMock(
        return_value={
            "sub": "user-id",
            "email": "user@example.com",
            "user_metadata": {"username": "user"},
        }
    )
    monkeypatch.setattr("app.auth.login.supabase_sign_in", sign_in)
    monkeypatch.setattr("app.auth.login.validate_supabase_jwt", validate)
    settings = Settings(
        app_env="staging",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="public-key",
    )
    service = AsyncMock(spec=UserService)

    response = await perform_login(
        "user@example.com",
        "password",
        service=service,
        settings=settings,
    )

    sign_in.assert_awaited_once_with("user@example.com", "password", settings=settings)
    validate.assert_awaited_once_with("signed-token", settings=settings)
    assert response.access_token == "signed-token"
    assert response.user.id == "user-id"


async def test_dev_login_uses_in_memory_auth_store() -> None:
    """Dev login authenticates with the in-memory auth store when enabled."""
    reset_dev_users()
    upsert_dev_user(
        UserModel(
            id=101,
            username="memory-user",
            first_name="Memory",
            last_name="User",
            email="memory@example.com",
            password=None,
            phone=None,
            user_status=1,
        ),
        password="my-password",
    )
    settings = Settings(app_env="dev", dev_jwt_secret="test-dev-jwt-secret")
    service = AsyncMock(spec=UserService)

    response = await perform_login(
        "memory@example.com",
        "my-password",
        service=service,
        settings=settings,
    )

    assert response.user.id == "101"
    assert response.user.email == "memory@example.com"
    service.login.assert_not_called()


async def test_dev_login_disabled_flag_uses_service_path() -> None:
    """Dev login falls back to the service path when in-memory auth flag is disabled."""
    settings = Settings(app_env="dev", dev_in_memory_auth_enabled=False)
    service = AsyncMock(spec=UserService)
    service.login.return_value = "token"
    service.get_user.return_value = UserModel(
        id=10,
        username="service-user",
        first_name=None,
        last_name=None,
        email="service@example.com",
        password=None,
        phone=None,
        user_status=1,
    )

    response = await perform_login(
        "service-user",
        "password",
        service=service,
        settings=settings,
    )

    assert response.user.id == "10"
    service.login.assert_awaited_once()
