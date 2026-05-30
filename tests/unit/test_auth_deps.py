"""Unit tests for authentication dependency helpers."""

from __future__ import annotations

import pytest

from app.api.deps import resolve_current_user_from_token
from app.auth.dev_jwt import issue_dev_jwt
from app.auth.dev_store import get_dev_user_by_username
from app.config import Settings


def _dev_user() -> object:
    user = get_dev_user_by_username("devuser")
    assert user is not None
    return user


def test_resolve_current_user_from_valid_dev_token() -> None:
    """Development tokens resolve to the seeded in-memory user."""
    settings = Settings(app_env="dev", dev_jwt_secret="test-dev-jwt-secret")

    resolved = resolve_current_user_from_token(
        issue_dev_jwt(_dev_user(), settings.dev_jwt_secret),
        settings,
    )

    assert resolved.id == 1
    assert resolved.username == "devuser"


def test_resolve_current_user_from_token_uses_supabase_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging and production environments delegate to Supabase validation."""
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
