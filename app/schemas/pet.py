"""Compatibility wrapper for pet schemas from petstore_core."""

from petstore_core.schemas.pet import Category, Pet, PetBase, PetCreate, PetStatus, PetUpdate, Tag

__all__ = ["PetStatus", "Category", "Tag", "PetBase", "PetCreate", "PetUpdate", "Pet"]
