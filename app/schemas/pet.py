"""Pydantic schemas for Pet resources."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PetStatus(StrEnum):
    """Pet availability status."""

    available = "available"
    pending = "pending"
    sold = "sold"


class Category(BaseModel):
    """Pet category.

    Attributes:
        id: Category identifier.
        name: Category name.
    """

    id: int | None = None
    name: str | None = None


class Tag(BaseModel):
    """Pet tag.

    Attributes:
        id: Tag identifier.
        name: Tag name.
    """

    id: int | None = None
    name: str | None = None


class PetBase(BaseModel):
    """Base pet schema with shared fields.

    Attributes:
        name: Pet name.
        photo_urls: List of photo URLs.
        category: Pet category.
        tags: List of tags.
        status: Pet availability status.
    """

    name: str = Field(..., min_length=1)
    photo_urls: list[str] = Field(default_factory=list, alias="photoUrls")
    category: Category | None = None
    tags: list[Tag] | None = None
    status: PetStatus | None = PetStatus.available

    model_config = {"populate_by_name": True}


class PetCreate(PetBase):
    """Schema for creating a new pet."""

    pass


class PetUpdate(PetBase):
    """Schema for updating an existing pet.

    Attributes:
        id: Pet identifier (required for updates).
    """

    id: int


class Pet(PetBase):
    """Full pet schema including server-assigned fields.

    Attributes:
        id: Pet identifier.
    """

    id: int | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}
