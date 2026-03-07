"""In-memory User repository implementation."""

from __future__ import annotations

import asyncio

from app.schemas.user import User, UserCreate, UserUpdate


class MemoryUserRepository:
    """Thread-safe in-memory User repository backed by a dict.

    State is held in-process and lost on restart.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory user store."""
        self._store: dict[str, User] = {}
        self._counter: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by username.

        Args:
            username: The user's unique username.

        Returns:
            The user if found, else None.
        """
        return self._store.get(username)

    async def create(self, user: UserCreate) -> User:
        """Persist a new user.

        Args:
            user: User data to create.

        Returns:
            The created user with assigned ID.
        """
        async with self._lock:
            self._counter += 1
            new_id = self._counter
            new_user = User(
                id=new_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone=user.phone,
                user_status=user.user_status,
            )
            if user.username:
                self._store[user.username] = new_user
            return new_user

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
        async with self._lock:
            if username not in self._store:
                raise KeyError(f"User '{username}' not found")
            existing = self._store[username]
            updated = User(
                id=existing.id,
                username=user.username if user.username is not None else existing.username,
                first_name=user.first_name if user.first_name is not None else existing.first_name,
                last_name=user.last_name if user.last_name is not None else existing.last_name,
                email=user.email if user.email is not None else existing.email,
                phone=user.phone if user.phone is not None else existing.phone,
                user_status=(
                    user.user_status if user.user_status is not None else existing.user_status
                ),
            )
            # Update key if username changed
            new_username = updated.username or username
            if new_username != username:
                del self._store[username]
            self._store[new_username] = updated
            return updated

    async def delete(self, username: str) -> None:
        """Delete a user by username.

        Args:
            username: The user's unique username.

        Raises:
            KeyError: If user not found.
        """
        async with self._lock:
            if username not in self._store:
                raise KeyError(f"User '{username}' not found")
            del self._store[username]
