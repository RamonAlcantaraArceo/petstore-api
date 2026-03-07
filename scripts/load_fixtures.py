"""Load fixture data into the in-memory or local PostgreSQL store."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.dependencies import get_memory_pet_repo, get_memory_user_repo
from app.schemas.pet import PetCreate, PetStatus
from app.schemas.user import UserCreate
from app.services.pet import PetService
from app.services.user import UserService


async def load_fixtures() -> None:
    """Seed the store with sample pets and users."""
    pet_service = PetService(get_memory_pet_repo())
    user_service = UserService(get_memory_user_repo())

    # Create sample pets
    for name, status in [
        ("Buddy", PetStatus.available),
        ("Max", PetStatus.available),
        ("Charlie", PetStatus.pending),
        ("Bella", PetStatus.sold),
    ]:
        pet = await pet_service.add_pet(PetCreate(name=name, photoUrls=[], status=status))
        print(f"Created pet: {pet.id} - {pet.name} ({pet.status})")

    # Create sample users
    for username, email in [
        ("johndoe", "john@example.com"),
        ("janedoe", "jane@example.com"),
    ]:
        user = await user_service.create_user(
            UserCreate(username=username, email=email, password="secret")
        )
        print(f"Created user: {user.id} - {user.username}")


if __name__ == "__main__":
    asyncio.run(load_fixtures())
