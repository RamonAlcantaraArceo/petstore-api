"""Pet service — business logic layer delegating to the repository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, status

from app.repositories.base import PetRepository
from app.schemas.pet import Pet, PetCreate, PetUpdate


class PetService:
    """Service that encapsulates Pet business logic.

    Args:
        repo: A PetRepository implementation.
    """

    def __init__(
        self,
        repo: PetRepository,
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

    async def get_pet(self, pet_id: int) -> Pet:
        """Retrieve a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Returns:
            The pet if found.

        Raises:
            HTTPException: 404 if pet not found.
        """
        pet = await self._repo.get(pet_id)
        if pet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
        return pet

    async def find_by_status(
        self,
        pet_status: str | None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[Pet]:
        """Find pets by availability status with optional pagination.

        Args:
            pet_status: The status to filter by. When ``None``, all pets are
                returned regardless of status.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. When ``None``, all
                matching records are returned.

        Returns:
            List of matching pets.
        """
        return await self._repo.list_by_status(pet_status, skip=skip, limit=limit)

    async def find_by_tags(self, tags: list[str]) -> list[Pet]:
        """Find pets by tag names.

        Args:
            tags: Tag names to filter by.

        Returns:
            List of matching pets.
        """
        return await self._repo.list_by_tags(tags)

    async def add_pet(self, pet: PetCreate) -> Pet:
        """Add a new pet to the store.

        Args:
            pet: The pet data to create.

        Returns:
            The created Pet with assigned ID.

        Raises:
            ValueError: If pet name is empty.

        Example:
            >>> service = PetService(repo)
            >>> pet = await service.add_pet(PetCreate(name="Fido", photoUrls=[]))
            >>> assert pet.id is not None
        """
        if not pet.name or not pet.name.strip():
            raise ValueError("Pet name cannot be empty")
        try:
            created = await self._repo.create(pet)
            await self._commit()
            return created
        except Exception:
            await self._rollback()
            raise

    async def update_pet(self, pet: PetUpdate) -> Pet:
        """Update an existing pet.

        Args:
            pet: Updated pet data (must include id).

        Returns:
            The updated pet.

        Raises:
            HTTPException: 404 if pet not found.
        """
        try:
            updated = await self._repo.update(pet)
            await self._commit()
            return updated
        except KeyError as exc:
            await self._rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
            ) from exc
        except Exception:
            await self._rollback()
            raise

    async def delete_pet(self, pet_id: int) -> None:
        """Delete a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Raises:
            HTTPException: 404 if pet not found.
        """
        try:
            await self._repo.delete(pet_id)
            await self._commit()
        except KeyError as exc:
            await self._rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found"
            ) from exc
        except Exception:
            await self._rollback()
            raise

    async def update_pet_with_form(
        self,
        pet_id: int,
        name: str | None = None,
        status: str | None = None,
    ) -> Pet:
        """Update pet name and/or status via form data.

        Args:
            pet_id: The pet's unique identifier.
            name: New name for the pet (optional).
            status: New status for the pet (optional).

        Returns:
            The updated pet.

        Raises:
            HTTPException: 404 if pet not found.
        """
        pet = await self.get_pet(pet_id)
        from app.schemas.pet import PetStatus

        updated = PetUpdate(
            id=pet_id,
            name=name if name is not None else pet.name,
            photoUrls=pet.photo_urls,
            category=pet.category,
            tags=pet.tags,
            status=PetStatus(status) if status else pet.status,
        )
        return await self.update_pet(updated)
