"""Development-only in-memory user/auth store backed by ``UserModel``."""

from __future__ import annotations

from petstore_core.models.user import UserModel
from petstore_core.schemas.user import UserUpdate

PASSWORD_FIELD = "password"


def _seed_users() -> tuple[dict[int, UserModel], dict[int, str | None]]:
    """Return the default development users."""
    users = {
        1: UserModel(
            id=1,
            username="devuser",
            first_name="Dev",
            last_name="User",
            email="dev@example.com",
            **{PASSWORD_FIELD: None},
            phone="555-1234",
            user_status=1,
        ),
        2: UserModel(
            id=2,
            username="devadmin",
            first_name="Dev",
            last_name="Admin",
            email="devadmin@example.com",
            **{PASSWORD_FIELD: None},
            phone="555-5678",
            user_status=1,
        ),
    }
    passwords: dict[int, str | None] = {
        1: "dev-password-placeholder",
        2: "dev-password-placeholder",
    }
    return users, passwords


_DEV_USERS, _DEV_PASSWORDS = _seed_users()


def _copy_user(user: UserModel) -> UserModel:
    """Return a detached copy of a SQLAlchemy ``UserModel``."""
    return UserModel(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        **{PASSWORD_FIELD: None},
        phone=user.phone,
        user_status=user.user_status,
    )


def get_dev_user(user_id: int) -> UserModel | None:
    """Return a development user by identifier."""
    return _DEV_USERS.get(user_id)


def get_dev_user_by_username(username: str) -> UserModel | None:
    """Return a development user by username."""
    for user in _DEV_USERS.values():
        if user.username == username:
            return user
    return None


def get_dev_user_by_email(email: str) -> UserModel | None:
    """Return a development user by email."""
    target = email.strip().lower()
    for user in _DEV_USERS.values():
        if isinstance(user.email, str) and user.email.strip().lower() == target:
            return user
    return None


def authenticate_dev_user(identifier: str, password: str) -> UserModel | None:
    """Authenticate a development user by email or username."""
    user = get_dev_user_by_email(identifier) or get_dev_user_by_username(identifier)
    if user is None:
        return None
    stored_password = _DEV_PASSWORDS.get(user.id)
    if stored_password != password:
        return None
    return user


def upsert_dev_user(user: UserModel, *, password: str | None = None) -> UserModel:
    """Create or replace a development user in the in-memory auth store."""
    _DEV_USERS[user.id] = _copy_user(user)
    if password is not None:
        _DEV_PASSWORDS[user.id] = password
    elif user.id not in _DEV_PASSWORDS:
        _DEV_PASSWORDS[user.id] = None
    return _DEV_USERS[user.id]


def update_dev_user(username: str, user: UserUpdate) -> UserModel | None:
    """Update an in-memory development auth user by username."""
    existing = get_dev_user_by_username(username)
    if existing is None:
        return None

    updated = UserModel(
        id=existing.id,
        username=user.username if user.username is not None else existing.username,
        first_name=user.first_name if user.first_name is not None else existing.first_name,
        last_name=user.last_name if user.last_name is not None else existing.last_name,
        email=user.email if user.email is not None else existing.email,
        **{PASSWORD_FIELD: None},
        phone=user.phone if user.phone is not None else existing.phone,
        user_status=user.user_status if user.user_status is not None else existing.user_status,
    )
    password = user.password if user.password is not None else _DEV_PASSWORDS.get(existing.id)
    return upsert_dev_user(updated, password=password)


def delete_dev_user_by_id(user_id: int) -> None:
    """Delete a development user by identifier."""
    _DEV_USERS.pop(user_id, None)
    _DEV_PASSWORDS.pop(user_id, None)


def delete_dev_user_by_username(username: str) -> None:
    """Delete a development user by username."""
    user = get_dev_user_by_username(username)
    if user is None:
        return
    delete_dev_user_by_id(user.id)


def list_dev_users() -> tuple[UserModel, ...]:
    """Return all development users currently held in memory."""
    return tuple(_DEV_USERS.values())


def reset_dev_users() -> None:
    """Restore the seeded development users."""
    global _DEV_USERS, _DEV_PASSWORDS
    _DEV_USERS, _DEV_PASSWORDS = _seed_users()
