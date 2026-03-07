"""User service — business logic layer delegating to the repository."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.repositories.base import UserRepository
from app.schemas.user import User, UserCreate, UserUpdate


class UserService:
    """Service that encapsulates User business logic.

    Args:
        repo: A UserRepository implementation.
    """

    def __init__(self, repo: UserRepository) -> None:
        """Initialize the service with a repository.

        Args:
            repo: Repository implementation to delegate to.
        """
        self._repo = repo

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
        return await self._repo.create(user)

    async def create_users_with_list(self, users: list[UserCreate]) -> list[User]:
        """Create multiple users at once.

        Args:
            users: List of user data to create.

        Returns:
            List of created users.
        """
        return await self._repo.create_many(users)

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
            return await self._repo.update(username, user)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from exc

    async def delete_user(self, username: str) -> None:
        """Delete a user.

        Args:
            username: The user's unique username.

        Raises:
            HTTPException: 404 if user not found.
        """
        try:
            await self._repo.delete(username)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from exc

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
