"""Behavior tests for Supabase-specific user route orchestration."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from petstore_core.errors import NotFoundError
from petstore_core.models.user import UserModel
from petstore_core.schemas.user import User, UserCreate, UserUpdate
from petstore_core.services.user import UserService

from app.api.v1.users import (
    create_user,
    create_users_with_list,
    delete_user,
    get_current_user_profile,
    get_user_by_name,
    logout_user,
    update_user,
)
from app.auth.supabase_auth import SupabaseAuthNotConfiguredError
from app.config import Settings


def _settings(*, admin_key: str = "admin-key") -> Settings:
    """Return staging settings for route orchestration tests."""
    return Settings(
        app_env="staging",
        supabase_url="https://project.supabase.co",
        supabase_anon_key="public-key",
        supabase_service_role_key=admin_key,
    )


def _service() -> tuple[UserService, AsyncMock]:
    """Return a typed user service backed by an inspectable async mock."""
    mock = AsyncMock(spec=UserService)
    return cast(UserService, mock), mock


def _user(*, username: str = "user", email: str | None = "user@example.com") -> User:
    """Return a representative user response."""
    return User(
        id=1,
        username=username,
        first_name="Test",
        last_name="User",
        email=email,
        phone="555-0100",
        user_status=1,
    )


def _create_payload(
    *, username: str | None = "user", email: str | None = "user@example.com"
) -> UserCreate:
    """Return a representative user creation payload."""
    return UserCreate(
        username=username,
        first_name="Test",
        last_name="User",
        email=email,
        phone="555-0100",
        password="password",
        user_status=1,
    )


async def test_create_user_registers_supabase_then_mirrors_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging creation registers Auth first and mirrors the profile locally."""
    sign_up = AsyncMock(return_value={"id": "supabase-id"})
    monkeypatch.setattr("app.api.v1.users.supabase_sign_up", sign_up)
    service, mock = _service()
    mock.create_user.return_value = _user()
    payload = _create_payload()

    result = await create_user(payload, service, _settings())

    assert result.username == "user"
    sign_up.assert_awaited_once_with(
        "user@example.com",
        "password",
        metadata={
            "username": "user",
            "first_name": "Test",
            "last_name": "User",
            "phone": "555-0100",
            "user_status": 1,
        },
        settings=_settings(),
    )
    mirrored = mock.create_user.await_args.args[0]
    assert mirrored.username == "user"
    assert mirrored.email == "user@example.com"


async def test_create_user_requires_email_in_supabase_environment() -> None:
    """Staging creation rejects payloads that Supabase cannot identify."""
    service, _ = _service()

    with pytest.raises(HTTPException) as exc_info:
        await create_user(_create_payload(email=None), service, _settings())

    assert exc_info.value.status_code == 422


async def test_create_user_maps_missing_supabase_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging creation maps missing provider configuration to 503."""
    sign_up = AsyncMock(side_effect=SupabaseAuthNotConfiguredError)
    monkeypatch.setattr("app.api.v1.users.supabase_sign_up", sign_up)
    service, _ = _service()

    with pytest.raises(HTTPException) as exc_info:
        await create_user(_create_payload(), service, _settings())

    assert exc_info.value.status_code == 503


async def test_create_users_with_list_registers_and_mirrors_each_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bulk staging creation preserves one Auth and local write per user."""
    sign_up = AsyncMock(return_value={"id": "supabase-id"})
    monkeypatch.setattr("app.api.v1.users.supabase_sign_up", sign_up)
    service, mock = _service()
    mock.create_user.side_effect = [
        _user(username="first", email="first@example.com"),
        _user(username="second", email="second@example.com"),
    ]
    users = [
        _create_payload(username="first", email="first@example.com"),
        _create_payload(username="second", email="second@example.com"),
    ]

    result = await create_users_with_list(users, service, _settings())

    assert [user.username for user in result] == ["first", "second"]
    assert sign_up.await_count == 2
    assert mock.create_user.await_count == 2


async def test_create_users_with_list_rejects_first_missing_email() -> None:
    """Bulk staging creation stops before registering an unidentified user."""
    service, _ = _service()

    with pytest.raises(HTTPException) as exc_info:
        await create_users_with_list([_create_payload(email=None)], service, _settings())

    assert exc_info.value.status_code == 422
    assert "missing for username='user'" in str(exc_info.value.detail)


async def test_logout_revokes_supabase_session_before_local_logout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging logout revokes the bearer session and completes local cleanup."""
    sign_out = AsyncMock()
    monkeypatch.setattr("app.api.v1.users.supabase_sign_out", sign_out)
    service, mock = _service()
    mock.logout.return_value = None
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")

    result = await logout_user(credentials, service, _settings())

    assert result == {"message": "User logged out"}
    sign_out.assert_awaited_once_with("access-token", settings=_settings())
    mock.logout.assert_awaited_once()


async def test_logout_continues_when_supabase_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Logout remains safe when session revocation cannot be configured."""
    sign_out = AsyncMock(side_effect=SupabaseAuthNotConfiguredError)
    monkeypatch.setattr("app.api.v1.users.supabase_sign_out", sign_out)
    service, mock = _service()
    mock.logout.return_value = None
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")

    result = await logout_user(credentials, service, _settings())

    assert result == {"message": "User logged out"}
    mock.logout.assert_awaited_once()


async def test_current_user_profile_maps_authenticated_model() -> None:
    """The profile route preserves authenticated JWT-derived user details."""
    current_user = UserModel(
        id=7,
        username="user",
        first_name="Test",
        last_name="User",
        email="user@example.com",
        phone="555-0100",
        user_status=1,
    )

    result = await get_current_user_profile(current_user)

    assert result.id == 7
    assert result.email == "user@example.com"


async def test_username_lookup_is_rejected_in_supabase_environment() -> None:
    """Staging directs callers away from unsupported username lookup."""
    service, _ = _service()

    with pytest.raises(HTTPException) as exc_info:
        await get_user_by_name("user", service, _settings())

    assert exc_info.value.status_code == 501
    assert "GET /user/me" in str(exc_info.value.detail)


async def test_update_user_syncs_profile_fields_to_supabase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging updates synchronize supplied profile fields before local storage."""
    update_supabase = AsyncMock(return_value={"id": "supabase-id"})
    monkeypatch.setattr("app.api.v1.users.supabase_update_user", update_supabase)
    service, mock = _service()
    mock.update_user.return_value = _user(email="new@example.com")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")
    update = UserUpdate(
        email="new@example.com",
        first_name="New",
        last_name="Name",
        phone="555-9999",
        user_status=2,
    )

    result = await update_user("user", update, credentials, service, _settings())

    assert result.email == "new@example.com"
    update_supabase.assert_awaited_once_with(
        "access-token",
        email="new@example.com",
        phone="555-9999",
        metadata={
            "first_name": "New",
            "last_name": "Name",
            "phone": "555-9999",
            "user_status": 2,
        },
        settings=_settings(),
    )
    mock.update_user.assert_awaited_once_with("user", update)


async def test_update_user_rejects_username_changes() -> None:
    """Staging rejects username changes before contacting either backend."""
    service, mock = _service()

    with pytest.raises(HTTPException) as exc_info:
        await update_user(
            "user",
            UserUpdate(username="renamed"),
            None,
            service,
            _settings(),
        )

    assert exc_info.value.status_code == 422
    mock.update_user.assert_not_awaited()


async def test_delete_user_resolves_email_and_falls_back_to_metadata_username(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deletion removes Supabase identity then tries all local mirror identifiers."""
    get_supabase_user = AsyncMock(
        return_value={
            "id": "supabase-id",
            "email": "user@example.com",
            "user_metadata": {"username": "metadata-user"},
        }
    )
    delete_supabase_user = AsyncMock()
    monkeypatch.setattr("app.api.v1.users.supabase_get_user_by_email", get_supabase_user)
    monkeypatch.setattr("app.api.v1.users.supabase_delete_user", delete_supabase_user)
    service, mock = _service()
    mock.get_user.return_value = _user()
    mock.delete_user.side_effect = [
        NotFoundError("missing username"),
        NotFoundError("missing email"),
        None,
    ]

    await delete_user("user", service, _settings())

    get_supabase_user.assert_awaited_once_with("user@example.com", settings=_settings())
    delete_supabase_user.assert_awaited_once_with("supabase-id", settings=_settings())
    assert [call.args[0] for call in mock.delete_user.await_args_list] == [
        "user",
        "user@example.com",
        "metadata-user",
    ]


async def test_delete_user_cleans_local_profile_when_supabase_user_is_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing Supabase identity does not prevent local mirror cleanup."""
    get_supabase_user = AsyncMock(side_effect=HTTPException(status_code=404, detail="not found"))
    delete_supabase_user = AsyncMock()
    monkeypatch.setattr("app.api.v1.users.supabase_get_user_by_email", get_supabase_user)
    monkeypatch.setattr("app.api.v1.users.supabase_delete_user", delete_supabase_user)
    service, mock = _service()
    mock.delete_user.return_value = None

    await delete_user("user@example.com", service, _settings())

    delete_supabase_user.assert_not_awaited()
    mock.delete_user.assert_awaited_once_with("user@example.com")


async def test_delete_user_requires_admin_key() -> None:
    """Staging deletion fails before lookup when no server-side key is configured."""
    service, mock = _service()

    with pytest.raises(HTTPException) as exc_info:
        await delete_user("user@example.com", service, _settings(admin_key=""))

    assert exc_info.value.status_code == 501
    mock.delete_user.assert_not_awaited()


async def test_delete_user_requires_profile_email_for_username_target() -> None:
    """Username deletion cannot resolve Supabase identity without a mirrored email."""
    service, mock = _service()
    mock.get_user.return_value = _user(email=None)

    with pytest.raises(HTTPException) as exc_info:
        await delete_user("user", service, _settings())

    assert exc_info.value.status_code == 422
