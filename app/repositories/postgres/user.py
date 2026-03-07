"""Async SQLAlchemy User repository implementation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserModel
from app.schemas.user import User, UserCreate, UserUpdate


def _model_to_schema(model: UserModel) -> User:
    """Convert a UserModel ORM instance to a User schema.

    Args:
        model: The SQLAlchemy ORM user model.

    Returns:
        A User Pydantic schema instance.
    """
    id_val: Any = model.id
    username_val: Any = model.username
    first_name_val: Any = model.first_name
    last_name_val: Any = model.last_name
    email_val: Any = model.email
    phone_val: Any = model.phone
    status_val: Any = model.user_status
    return User(
        id=id_val,
        username=username_val,
        first_name=first_name_val,
        last_name=last_name_val,
        email=email_val,
        phone=phone_val,
        user_status=status_val,
    )


class PostgresUserRepository:
    """Async SQLAlchemy User repository implementation.

    Args:
        session: An async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: Async SQLAlchemy session to use for queries.
        """
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by username.

        Args:
            username: The user's unique username.

        Returns:
            The user if found, else None.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        return _model_to_schema(model) if model else None

    async def create(self, user: UserCreate) -> User:
        """Persist a new user.

        Args:
            user: User data to create.

        Returns:
            The created user with assigned ID.
        """
        model = UserModel(
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            password=user.password,
            phone=user.phone,
            user_status=user.user_status,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _model_to_schema(model)

    async def create_many(self, users: list[UserCreate]) -> list[User]:
        """Persist multiple users at once.

        Args:
            users: List of user data to create.

        Returns:
            List of created users.
        """
        result = []
        for user in users:
            result.append(await self.create(user))
        return result

    async def update(self, username: str, user: UserUpdate) -> User:
        """Update an existing user.

        Args:
            username: The user's current username.
            user: Updated user data.

        Returns:
            The updated user.

        Raises:
            KeyError: If user not found.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise KeyError(f"User '{username}' not found")
        if user.username is not None:
            model.username = user.username  # type: ignore[assignment]
        if user.first_name is not None:
            model.first_name = user.first_name  # type: ignore[assignment]
        if user.last_name is not None:
            model.last_name = user.last_name  # type: ignore[assignment]
        if user.email is not None:
            model.email = user.email  # type: ignore[assignment]
        if user.phone is not None:
            model.phone = user.phone  # type: ignore[assignment]
        if user.user_status is not None:
            model.user_status = user.user_status  # type: ignore[assignment]
        await self._session.flush()
        await self._session.refresh(model)
        return _model_to_schema(model)

    async def delete(self, username: str) -> None:
        """Delete a user by username.

        Args:
            username: The user's unique username.

        Raises:
            KeyError: If user not found.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise KeyError(f"User '{username}' not found")
        await self._session.delete(model)
        await self._session.flush()
