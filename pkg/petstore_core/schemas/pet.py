"""Pydantic schemas for Pet resources."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field


class PetStatus(StrEnum):
    """Pet availability status."""

    available = "available"
    pending = "pending"
    sold = "sold"


class Category(BaseModel):
    """Pet category.
    \f
    Attributes:
        id: Category identifier.
        name: Category name.
    """

    id: Annotated[int | None, Field(gt=0, description="Category identifier")] = None
    name: Annotated[str | None, Field(description="Category name")] = None


class Tag(BaseModel):
    """Pet tag.
    \f
    Attributes:
        id: Tag identifier.
        name: Tag name.
    """

    id: Annotated[int | None, Field(gt=0, description="Tag identifier")] = None
    name: Annotated[str | None, Field(description="Tag name")] = None


class PetBase(BaseModel):
    """Base pet schema with shared fields.

    Attributes:
        name: Pet name.
        photo_urls: List of photo URLs.
        category: Pet category.
        tags: List of tags.
        status: Pet availability status.
    """

    name: Annotated[str, Field(..., min_length=1, description="Pet name (required)")]
    photo_urls: Annotated[
        list[str], Field(default_factory=list, alias="photoUrls", description="List of photo URLs")
    ]
    category: Annotated[Category | None, Field(description="Pet category")] = None
    tags: Annotated[list[Tag] | None, Field(description="List of tags")] = None
    status: Annotated[PetStatus | None, Field(description="Pet availability status")] = (
        PetStatus.available
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


class PetCreate(PetBase):
    """Schema for creating a new pet."""

    pass


class PetUpdate(PetBase):
    """Schema for updating an existing pet.
    \f
    Attributes:
        id: Pet identifier (required for updates).
    """

    id: Annotated[int, Field(gt=0, description="Pet identifier (required for updates)")]


class Pet(PetBase):
    """Full pet schema including server-assigned fields.
    \f
    Attributes:
        id: Pet identifier.
    """

    id: Annotated[int | None, Field(gt=0, description="Pet identifier")] = None

    model_config = {"from_attributes": True, "populate_by_name": True}
