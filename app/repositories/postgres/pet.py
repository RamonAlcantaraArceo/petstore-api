"""Async SQLAlchemy Pet repository implementation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pet import PetModel
from app.schemas.pet import Category, Pet, PetCreate, PetStatus, PetUpdate, Tag


def _model_to_schema(model: PetModel) -> Pet:
    """Convert a PetModel ORM instance to a Pet schema.

    Args:
        model: The SQLAlchemy ORM pet model.

    Returns:
        A Pet Pydantic schema instance.
    """
    category_data: Any = model.category
    category = Category(**category_data) if isinstance(category_data, dict) else None
    tags_data: Any = model.tags
    tags_raw: list[Any] = tags_data if isinstance(tags_data, list) else []
    tags = [Tag(**t) for t in tags_raw if isinstance(t, dict)]
    name_val: Any = model.name
    photo_val: Any = model.photo_urls
    status_val: Any = model.status
    return Pet(
        id=model.id,
        name=name_val,
        photoUrls=photo_val or [],
        category=category,
        tags=tags,
        status=PetStatus(status_val) if status_val else PetStatus.available,
    )


class PostgresPetRepository:
    """Async SQLAlchemy Pet repository implementation.

    Args:
        session: An async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: Async SQLAlchemy session to use for queries.
        """
        self._session = session

    async def get(self, pet_id: int) -> Pet | None:
        """Retrieve a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Returns:
            The pet if found, else None.
        """
        result = await self._session.execute(select(PetModel).where(PetModel.id == pet_id))
        model = result.scalar_one_or_none()
        return _model_to_schema(model) if model else None

    async def list_by_status(
        self,
        status: str | None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[Pet]:
        """List pets filtered by status with optional pagination.

        Args:
            status: Availability status to filter by. When ``None``, all pets
                are returned regardless of status.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. When ``None``, all
                matching records are returned.

        Returns:
            List of matching pets.
        """
        stmt = select(PetModel)
        if status is not None:
            stmt = stmt.where(PetModel.status == status)
        stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [_model_to_schema(m) for m in result.scalars().all()]

    async def list_by_tags(self, tags: list[str]) -> list[Pet]:
        """List pets filtered by tag names.

        Args:
            tags: Tag names to filter by.

        Returns:
            List of matching pets.
        """
        result = await self._session.execute(select(PetModel))
        pets = []
        for model in result.scalars().all():
            tags_data: Any = model.tags
            if isinstance(tags_data, list):
                model_tag_names = {t.get("name") for t in tags_data if isinstance(t, dict)}
                if model_tag_names.intersection(tags):
                    pets.append(_model_to_schema(model))
        return pets

    async def create(self, pet: PetCreate) -> Pet:
        """Persist a new pet.

        Args:
            pet: Pet data to create.

        Returns:
            The created pet with assigned ID.
        """
        category = pet.category.model_dump() if pet.category else None
        tags = [t.model_dump() for t in pet.tags] if pet.tags is not None else None
        model = PetModel(
            name=pet.name,
            status=(pet.status or PetStatus.available).value,
            photo_urls=pet.photo_urls,
            category=category,
            tags=tags,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _model_to_schema(model)

    async def update(self, pet: PetUpdate) -> Pet:
        """Update an existing pet.

        Args:
            pet: Updated pet data (must include id).

        Returns:
            The updated pet.

        Raises:
            KeyError: If pet not found.
        """
        result = await self._session.execute(select(PetModel).where(PetModel.id == pet.id))
        model = result.scalar_one_or_none()
        if not model:
            raise KeyError(f"Pet {pet.id} not found")
        model.name = pet.name  # type: ignore[assignment]
        model.status = (pet.status or PetStatus.available).value  # type: ignore[assignment]
        model.photo_urls = pet.photo_urls  # type: ignore[assignment]
        model.category = pet.category.model_dump() if pet.category else None  # type: ignore[assignment]
        model.tags = [t.model_dump() for t in pet.tags] if pet.tags is not None else None  # type: ignore[assignment]
        await self._session.flush()
        await self._session.refresh(model)
        return _model_to_schema(model)

    async def delete(self, pet_id: int) -> None:
        """Delete a pet by ID.

        Args:
            pet_id: The pet's unique identifier.

        Raises:
            KeyError: If pet not found.
        """
        result = await self._session.execute(select(PetModel).where(PetModel.id == pet_id))
        model = result.scalar_one_or_none()
        if not model:
            raise KeyError(f"Pet {pet_id} not found")
        await self._session.delete(model)
        await self._session.flush()
