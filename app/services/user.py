"""User service — business logic layer delegating to the repository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, status

from app.repositories.base import UserRepository
from app.schemas.user import User, UserCreate, UserUpdate


class UserService:
    """Service that encapsulates User business logic.

    Args:
        repo: A UserRepository implementation.
    """

    def __init__(
        self,
        repo: UserRepository,
        commit: Callable[[], Awaitable[None]] | None = None,
        rollback: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the service with a repository.

        Args:
            repo: Repository implementation to delegate to.
            commit: Optional async transaction commit callback.
            rollback: Optional async transaction rollback callback.
        """
        self._repo = repo
        self._commit_callback = commit
        self._rollback_callback = rollback

    async def _commit(self) -> None:
        """Commit the current transaction when a callback is configured."""
        if self._commit_callback is not None:
            await self._commit_callback()

    async def _rollback(self) -> None:
        """Rollback the current transaction when a callback is configured."""
        if self._rollback_callback is not None:
            await self._rollback_callback()

    async def create_user(self, user: UserCreate) -> User:
        """Create a new user.

        Args:
            user: User data to create.

        Returns:
            The created User with assigned ID.

        Raises:
            ValueError: If username is empty.

        Example:
            >>> service = UserService(repo)
            >>> user = await service.create_user(UserCreate(username="johndoe"))
            >>> assert user.id is not None
        """
        if not user.username or not user.username.strip():
            raise ValueError("Username cannot be empty")
        try:
            created = await self._repo.create(user)
            await self._commit()
            return created
        except Exception:
            await self._rollback()
            raise

    async def create_users_with_list(self, users: list[UserCreate]) -> list[User]:
        """Create multiple users at once.

        Args:
            users: List of user data to create.

        Returns:
            List of created users.
        """
        try:
            created = await self._repo.create_many(users)
            await self._commit()
            return created
        except Exception:
            await self._rollback()
            raise

    async def get_user(self, username: str) -> User:
        """Retrieve a user by username.

        Args:
            username: The user's unique username.

        Returns:
            The user if found.

        Raises:
            HTTPException: 404 if user not found.
        """
        user = await self._repo.get_by_username(username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def update_user(self, username: str, user: UserUpdate) -> User:
        """Update an existing user.

        Args:
            username: The user's current username.
            user: Updated user data.

        Returns:
            The updated user.

        Raises:
            HTTPException: 404 if user not found.
        """
        try:
            updated = await self._repo.update(username, user)
            await self._commit()
            return updated
        except KeyError as exc:
            await self._rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from exc
        except Exception:
            await self._rollback()
            raise

    async def delete_user(self, username: str) -> None:
        """Delete a user.

        Args:
            username: The user's unique username.

        Raises:
            HTTPException: 404 if user not found.
        """
        try:
            await self._repo.delete(username)
            await self._commit()
        except KeyError as exc:
            await self._rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from exc
        except Exception:
            await self._rollback()
            raise

    async def login(self, username: str, password: str) -> str:
        """Authenticate a user and return a session token.

        Args:
            username: The user's username.
            password: The user's password.

        Returns:
            A session token string.

        Raises:
            HTTPException: 400 if credentials are invalid.
        """
        user = await self._repo.get_by_username(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or password"
            )
        # In a production system this would verify the hashed password.
        return f"token-{username}"

    async def logout(self) -> None:
        """Log out the current user.

        In a stateless API this is a no-op; the client discards the token.
        """
        return None
