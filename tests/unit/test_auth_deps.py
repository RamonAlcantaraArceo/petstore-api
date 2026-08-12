"""Unit tests for authentication dependency helpers."""

from __future__ import annotations

import pytest

from app.api.deps import _sub_to_user_id, resolve_current_user_from_token
from app.auth.dev_jwt import issue_dev_jwt
from app.auth.dev_store import get_dev_user_by_username
from app.config import Settings


async def test_resolve_current_user_from_token_handles_uuid_sub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supabase UUID ``sub`` claims are mapped to a stable positive integer id."""
    supabase_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    settings = Settings(app_env="staging")

    async def _fake_validate(token: str, *, settings: Settings) -> dict[str, object]:
        return {
            "sub": supabase_uuid,
            "email": "uuid-user@example.com",
            "user_metadata": {},
        }

    monkeypatch.setattr("app.api.deps.validate_supabase_jwt", _fake_validate)

    resolved = await resolve_current_user_from_token("supabase-token", settings)

    assert resolved.id is not None
    assert resolved.id > 0
    assert resolved.email == "uuid-user@example.com"


class TestSubToUserId:
    def test_integer_string_returns_integer(self) -> None:
        assert _sub_to_user_id("42") == 42

    def test_uuid_string_returns_stable_positive_int(self) -> None:
        uid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        result = _sub_to_user_id(uid)
        assert result is not None
        assert result > 0
        # Stable across calls
        assert _sub_to_user_id(uid) == result

    def test_none_returns_none(self) -> None:
        assert _sub_to_user_id(None) is None

    def test_invalid_string_returns_none(self) -> None:
        assert _sub_to_user_id("not-a-uuid-or-int") is None


def _dev_user() -> object:
    user = get_dev_user_by_username("devuser")
    assert user is not None
    return user


async def test_resolve_current_user_from_valid_dev_token() -> None:
    """Development tokens resolve to the seeded in-memory user."""
    settings = Settings(app_env="dev", dev_jwt_secret="test-dev-jwt-secret")

    resolved = await resolve_current_user_from_token(
        issue_dev_jwt(_dev_user(), settings.dev_jwt_secret),
        settings,
    )

    assert resolved.id == 1
    assert resolved.username == "devuser"


async def test_resolve_current_user_from_token_uses_supabase_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging and production environments delegate to Supabase validation."""
    settings = Settings(app_env="staging")

    async def _fake_validate(token: str, *, settings: Settings) -> dict[str, object]:
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

    resolved = await resolve_current_user_from_token("supabase-token", settings)

    assert resolved.id == 42
    assert resolved.username == "stage-user"


async def test_resolve_current_user_from_token_uses_supabase_when_dev_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dev environment can delegate token validation to Supabase when flag is disabled."""
    settings = Settings(app_env="dev", dev_in_memory_auth_enabled=False)

    async def _fake_validate(token: str, *, settings: Settings) -> dict[str, object]:
        assert token == "supabase-token"
        assert settings.app_env == "dev"
        return {
            "sub": "42",
            "email": "dev-supabase@example.com",
            "user_metadata": {"username": "dev-supabase-user"},
        }

    monkeypatch.setattr("app.api.deps.validate_supabase_jwt", _fake_validate)

    resolved = await resolve_current_user_from_token("supabase-token", settings)

    assert resolved.id == 42
    assert resolved.email == "dev-supabase@example.com"
