"""Unit tests for the shared user login service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from petstore_core.config import Settings
from petstore_core.services.user import UserService

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
