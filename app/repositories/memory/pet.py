"""In-memory Pet repository implementation."""

from __future__ import annotations

import asyncio

from app.schemas.pet import Category, Pet, PetCreate, PetStatus, PetUpdate, Tag


class MemoryPetRepository:
    """Thread-safe in-memory Pet repository backed by a dict.

    State is held in-process and lost on restart.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory pet store."""
        self._store: dict[int, Pet] = {}
        self._counter: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, pet_id: int) -> Pet | None:
        """Retrieve a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Returns:
            The pet if found, else None.
        """
        return self._store.get(pet_id)

    async def list_by_status(self, status: str) -> list[Pet]:
        """List pets filtered by status.

        Args:
            status: Availability status to filter by.

        Returns:
            List of matching pets.
        """
        return [p for p in self._store.values() if p.status and p.status.value == status]

    async def list_by_tags(self, tags: list[str]) -> list[Pet]:
        """List pets filtered by tag names.

        Args:
            tags: Tag names to filter by.

        Returns:
            List of matching pets.
        """
        result = []
        for pet in self._store.values():
            if pet.tags:
                pet_tag_names = {t.name for t in pet.tags if t.name}
                if pet_tag_names.intersection(tags):
                    result.append(pet)
        return result

    async def create(self, pet: PetCreate) -> Pet:
        """Persist a new pet.

        Args:
            pet: Pet data to create.

        Returns:
            The created pet with assigned ID.
        """
        async with self._lock:
            self._counter += 1
            new_id = self._counter
            category = (
                Category(id=pet.category.id, name=pet.category.name) if pet.category else None
            )
            tags = [Tag(id=t.id, name=t.name) for t in pet.tags] if pet.tags is not None else None
            new_pet = Pet(
                id=new_id,
                name=pet.name,
                photoUrls=pet.photo_urls,
                category=category,
                tags=tags,
                status=pet.status or PetStatus.available,
            )
            self._store[new_id] = new_pet
            return new_pet

    async def update(self, pet: PetUpdate) -> Pet:
        """Update an existing pet.

        Args:
            pet: Updated pet data (must include id).

        Returns:
            The updated pet.

        Raises:
            KeyError: If pet not found.
        """
        async with self._lock:
            if pet.id not in self._store:
                raise KeyError(f"Pet {pet.id} not found")
            category = (
                Category(id=pet.category.id, name=pet.category.name) if pet.category else None
            )
            tags = [Tag(id=t.id, name=t.name) for t in pet.tags] if pet.tags is not None else None
            updated = Pet(
                id=pet.id,
                name=pet.name,
                photoUrls=pet.photo_urls,
                category=category,
                tags=tags,
                status=pet.status or PetStatus.available,
            )
            self._store[pet.id] = updated
            return updated

    async def delete(self, pet_id: int) -> None:
        """Delete a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Raises:
            KeyError: If pet not found.
        """
        async with self._lock:
            if pet_id not in self._store:
                raise KeyError(f"Pet {pet_id} not found")
            del self._store[pet_id]
