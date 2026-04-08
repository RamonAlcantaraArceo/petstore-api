"""Unit tests for UserService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user import UserService
from tests.factories.user import UserCreateFactory


def make_service(
    repo: AsyncMock, commit: AsyncMock | None = None, rollback: AsyncMock | None = None
) -> UserService:
    """Build a UserService around a mock repository.

    Args:
        repo: The mocked user repository.

    Returns:
        UserService using the mock.
    """
    return UserService(repo, commit=commit, rollback=rollback)


@pytest.mark.asyncio
async def test_create_user_delegates_to_repo() -> None:
    """create_user delegates creation to the repository."""
    repo = AsyncMock()
    user_data = UserCreateFactory()
    expected = User(id=1, username=user_data.username)
    repo.create.return_value = expected

    service = make_service(repo)
    result = await service.create_user(user_data)

    repo.create.assert_called_once_with(user_data)
    assert result.id == 1


@pytest.mark.asyncio
async def test_create_user_raises_value_error_for_empty_username() -> None:
    """create_user raises ValueError when username is empty."""
    repo = AsyncMock()
    service = make_service(repo)

    with pytest.raises(ValueError, match="Username cannot be empty"):
        await service.create_user(UserCreate(username=""))


@pytest.mark.asyncio
async def test_get_user_returns_user() -> None:
    """get_user returns the user when found."""
    repo = AsyncMock()
    user = User(id=1, username="johndoe")
    repo.get_by_username.return_value = user

    service = make_service(repo)
    result = await service.get_user("johndoe")

    assert result.username == "johndoe"


@pytest.mark.asyncio
async def test_get_user_raises_404_when_not_found() -> None:
    """get_user raises HTTPException 404 when user is not found."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.get_by_username.return_value = None

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.get_user("nobody")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_user_delegates_to_repo() -> None:
    """update_user delegates to the repository."""
    repo = AsyncMock()
    user_update = UserUpdate(first_name="Jane")
    expected = User(id=1, username="johndoe", first_name="Jane")
    repo.update.return_value = expected

    service = make_service(repo)
    result = await service.update_user("johndoe", user_update)

    repo.update.assert_called_once_with("johndoe", user_update)
    assert result.first_name == "Jane"


@pytest.mark.asyncio
async def test_update_user_raises_404_when_not_found() -> None:
    """update_user raises HTTPException 404 when user does not exist."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.update.side_effect = KeyError("User not found")

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.update_user("nobody", UserUpdate(first_name="Jane"))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_calls_repo() -> None:
    """delete_user calls repository delete."""
    repo = AsyncMock()
    repo.delete.return_value = None

    service = make_service(repo)
    await service.delete_user("johndoe")

    repo.delete.assert_called_once_with("johndoe")


@pytest.mark.asyncio
async def test_delete_user_raises_404_when_not_found() -> None:
    """delete_user raises HTTPException 404 when user not found."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.delete.side_effect = KeyError("User not found")

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_user("nobody")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_login_returns_token() -> None:
    """login returns a session token."""
    repo = AsyncMock()
    user = User(id=1, username="johndoe")
    repo.get_by_username.return_value = user

    service = make_service(repo)
    token = await service.login("johndoe", "password")

    assert "johndoe" in token


@pytest.mark.asyncio
async def test_login_raises_400_for_invalid_user() -> None:
    """login raises HTTPException 400 for non-existent user."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.get_by_username.return_value = None

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.login("nobody", "password")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_users_with_list() -> None:
    """create_users_with_list delegates to repository create_many."""
    repo = AsyncMock()
    users: list[UserCreate] = [UserCreateFactory() for _ in range(3)]
    expected = [User(id=i + 1, username=u.username) for i, u in enumerate(users)]
    repo.create_many.return_value = expected

    service = make_service(repo)
    result = await service.create_users_with_list(users)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_create_user_commits_when_callback_is_configured() -> None:
    """create_user calls commit callback after successful write."""
    repo = AsyncMock()
    user_data = UserCreateFactory()
    expected = User(id=1, username=user_data.username)
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()

    service = UserService(repo, commit=commit, rollback=rollback)
    await service.create_user(user_data)

    commit.assert_awaited_once()
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_rolls_back_on_unexpected_error() -> None:
    """update_user rolls back and re-raises for non-domain repository errors."""
    repo = AsyncMock()
    repo.update.side_effect = RuntimeError("db down")
    commit = AsyncMock()
    rollback = AsyncMock()

    service = UserService(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db down"):
        await service.update_user("johndoe", UserUpdate(first_name="Jane"))

    commit.assert_not_called()
    rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_returns_none():
    repo = AsyncMock()
    service = make_service(repo)

    result = await service.logout()
    assert result is None


@pytest.mark.asyncio
async def test_logout_does_not_raise():
    repo = AsyncMock()
    service = make_service(repo)
    try:
        await service.logout()
    except Exception as exc:
        pytest.fail(f"logout() raised an exception: {exc}")


@pytest.mark.asyncio
async def test_logout_does_not_call_commit_or_rollback():
    repo = AsyncMock()
    commit = AsyncMock()
    rollback = AsyncMock()

    service = UserService(repo, commit=commit, rollback=rollback)

    await service.logout()
    commit.assert_not_awaited()
    rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_user_calls_repo_delete():
    repo = AsyncMock()
    repo.delete.return_value = None
    service = make_service(repo)
    await service.delete_user("johndoe")
    repo.delete.assert_called_once_with("johndoe")


@pytest.mark.asyncio
async def test_delete_user_calls_commit_on_success():
    repo = AsyncMock()
    repo.delete.return_value = None
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.delete_user("johndoe")
    commit.assert_awaited_once()
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_raises_404_on_keyerror():
    repo = AsyncMock()
    repo.delete.side_effect = KeyError("not found")
    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_user("nobody")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_calls_rollback_on_keyerror():
    repo = AsyncMock()
    repo.delete.side_effect = KeyError("not found")
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    with pytest.raises(HTTPException):
        await service.delete_user("nobody")
    rollback.assert_awaited_once()
    commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_calls_rollback_and_reraises_on_other_exception():
    repo = AsyncMock()
    repo.delete.side_effect = RuntimeError("db error")
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db error"):
        await service.delete_user("johndoe")
    rollback.assert_awaited_once()
    commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_does_not_call_rollback_on_success():
    repo = AsyncMock()
    repo.delete.return_value = None
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.delete_user("johndoe")
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_users_with_list_delegates_to_repo():
    repo = AsyncMock()
    users: list[UserCreate] = [UserCreateFactory() for _ in range(2)]
    expected = [User(id=i + 1, username=u.username) for i, u in enumerate(users)]
    repo.create_many.return_value = expected
    service = make_service(repo)
    result = await service.create_users_with_list(users)
    repo.create_many.assert_called_once_with(users)
    assert result == expected


@pytest.mark.asyncio
async def test_create_users_with_list_returns_created_users():
    repo = AsyncMock()
    users: list[UserCreate] = [UserCreateFactory() for _ in range(3)]
    expected = [User(id=i + 1, username=u.username) for i, u in enumerate(users)]
    repo.create_many.return_value = expected
    service = make_service(repo)
    result = await service.create_users_with_list(users)
    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(u, User) for u in result)


@pytest.mark.asyncio
async def test_create_users_with_list_calls_commit_on_success():
    repo = AsyncMock()
    users: list[UserCreate] = [UserCreateFactory() for _ in range(2)]
    expected = [User(id=i + 1, username=u.username) for i, u in enumerate(users)]
    repo.create_many.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.create_users_with_list(users)
    commit.assert_awaited_once()
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_users_with_list_rolls_back_and_reraises_on_exception():
    repo = AsyncMock()
    users: list[UserCreate] = [UserCreateFactory() for _ in range(2)]
    repo.create_many.side_effect = RuntimeError("db error")
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db error"):
        await service.create_users_with_list(users)
    rollback.assert_awaited_once()
    commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_users_with_list_does_not_call_rollback_on_success():
    repo = AsyncMock()
    users: list[UserCreate] = [UserCreateFactory() for _ in range(2)]
    expected = [User(id=i + 1, username=u.username) for i, u in enumerate(users)]
    repo.create_many.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.create_users_with_list(users)
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_calls_commit_on_success():
    repo = AsyncMock()
    user_data = UserCreate(username="johndoe")
    expected = User(id=1, username="johndoe")
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.create_user(user_data)
    commit.assert_awaited_once()
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_calls_rollback_and_reraises_on_exception():
    repo = AsyncMock()
    user_data = UserCreate(username="johndoe")
    repo.create.side_effect = RuntimeError("db error")
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db error"):
        await service.create_user(user_data)
    rollback.assert_awaited_once()
    commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_does_not_call_rollback_on_success():
    repo = AsyncMock()
    user_data = UserCreate(username="johndoe")
    expected = User(id=1, username="johndoe")
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.create_user(user_data)
    rollback.assert_not_called()
