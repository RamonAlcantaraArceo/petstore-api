"""Development-only in-memory user store backed by ``UserModel``."""

from __future__ import annotations

from app.models.user import UserModel

PASSWORD_FIELD = "password"


def _seed_users() -> dict[int, UserModel]:
    """Return the default development users."""
    return {
        1: UserModel(
            id=1,
            username="devuser",
            first_name="Dev",
            last_name="User",
            email="dev@example.com",
            **{PASSWORD_FIELD: "dev-password-placeholder"},
            phone="555-1234",
            user_status=1,
        ),
        2: UserModel(
            id=2,
            username="devadmin",
            first_name="Dev",
            last_name="Admin",
            email="devadmin@example.com",
            **{PASSWORD_FIELD: "dev-password-placeholder"},
            phone="555-5678",
            user_status=1,
        ),
    }


_DEV_USERS: dict[int, UserModel] = _seed_users()


def get_dev_user(user_id: int) -> UserModel | None:
    """Return a development user by identifier."""
    return _DEV_USERS.get(user_id)


def get_dev_user_by_username(username: str) -> UserModel | None:
    """Return a development user by username."""
    for user in _DEV_USERS.values():
        if user.username == username:
            return user
    return None


def list_dev_users() -> tuple[UserModel, ...]:
    """Return all seeded development users."""
    return tuple(_DEV_USERS.values())


def reset_dev_users() -> None:
    """Restore the seeded development users."""
    global _DEV_USERS
    _DEV_USERS = _seed_users()
