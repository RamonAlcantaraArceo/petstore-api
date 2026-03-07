"""Abstract base repository protocols for all entities."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.order import Order, OrderCreate
from app.schemas.pet import Pet, PetCreate, PetUpdate
from app.schemas.user import User, UserCreate, UserUpdate


@runtime_checkable
class PetRepository(Protocol):
    """Protocol defining the Pet repository interface."""

    async def get(self, pet_id: int) -> Pet | None:
        """Retrieve a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Returns:
            The pet if found, else None.
        """
        ...

    async def list_by_status(self, status: str) -> list[Pet]:
        """List pets filtered by status.

        Args:
            status: Availability status to filter by.

        Returns:
            List of matching pets.
        """
        ...

    async def list_by_tags(self, tags: list[str]) -> list[Pet]:
        """List pets filtered by tag names.

        Args:
            tags: Tag names to filter by.

        Returns:
            List of matching pets.
        """
        ...

    async def create(self, pet: PetCreate) -> Pet:
        """Persist a new pet.

        Args:
            pet: Pet data to create.

        Returns:
            The created pet with assigned ID.
        """
        ...

    async def update(self, pet: PetUpdate) -> Pet:
        """Update an existing pet.

        Args:
            pet: Updated pet data (must include id).

        Returns:
            The updated pet.

        Raises:
            KeyError: If pet not found.
        """
        ...

    async def delete(self, pet_id: int) -> None:
        """Delete a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Raises:
            KeyError: If pet not found.
        """
        ...


@runtime_checkable
class OrderRepository(Protocol):
    """Protocol defining the Order repository interface."""

    async def get(self, order_id: int) -> Order | None:
        """Retrieve an order by ID.

        Args:
            order_id: The order's unique identifier.

        Returns:
            The order if found, else None.
        """
        ...

    async def create(self, order: OrderCreate) -> Order:
        """Persist a new order.

        Args:
            order: Order data to create.

        Returns:
            The created order with assigned ID.
        """
        ...

    async def delete(self, order_id: int) -> None:
        """Delete an order by ID.

        Args:
            order_id: The order's unique identifier.

        Raises:
            KeyError: If order not found.
        """
        ...

    async def get_inventory(self) -> dict[str, int]:
        """Return inventory counts grouped by pet status.

        Returns:
            Dict mapping status string to count of pets with that status.
        """
        ...


@runtime_checkable
class UserRepository(Protocol):
    """Protocol defining the User repository interface."""

    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by username.

        Args:
            username: The user's unique username.

        Returns:
            The user if found, else None.
        """
        ...

    async def create(self, user: UserCreate) -> User:
        """Persist a new user.

        Args:
            user: User data to create.

        Returns:
            The created user with assigned ID.
        """
        ...

    async def create_many(self, users: list[UserCreate]) -> list[User]:
        """Persist multiple users at once.

        Args:
            users: List of user data to create.

        Returns:
            List of created users.
        """
        ...

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
        ...

    async def delete(self, username: str) -> None:
        """Delete a user by username.

        Args:
            username: The user's unique username.

        Raises:
            KeyError: If user not found.
        """
        ...
