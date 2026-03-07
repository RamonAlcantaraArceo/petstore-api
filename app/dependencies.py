"""FastAPI dependency injection — db session, auth, config, and service factories."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.repositories.memory.order import MemoryOrderRepository
from app.repositories.memory.pet import MemoryPetRepository
from app.repositories.memory.user import MemoryUserRepository
from app.services.order import OrderService
from app.services.pet import PetService
from app.services.user import UserService

# Singletons for in-memory mode
_memory_pet_repo: MemoryPetRepository | None = None
_memory_order_repo: MemoryOrderRepository | None = None
_memory_user_repo: MemoryUserRepository | None = None


def get_memory_pet_repo() -> MemoryPetRepository:
    """Return the shared in-memory Pet repository singleton.

    Returns:
        The shared MemoryPetRepository instance.
    """
    global _memory_pet_repo
    if _memory_pet_repo is None:
        _memory_pet_repo = MemoryPetRepository()
    return _memory_pet_repo


def get_memory_order_repo() -> MemoryOrderRepository:
    """Return the shared in-memory Order repository singleton.

    Returns:
        The shared MemoryOrderRepository instance.
    """
    global _memory_order_repo
    if _memory_order_repo is None:
        _memory_order_repo = MemoryOrderRepository()
    return _memory_order_repo


def get_memory_user_repo() -> MemoryUserRepository:
    """Return the shared in-memory User repository singleton.

    Returns:
        The shared MemoryUserRepository instance.
    """
    global _memory_user_repo
    if _memory_user_repo is None:
        _memory_user_repo = MemoryUserRepository()
    return _memory_user_repo


def reset_memory_repos() -> None:
    """Reset all in-memory repository singletons (used in tests).

    Example:
        >>> reset_memory_repos()
    """
    global _memory_pet_repo, _memory_order_repo, _memory_user_repo
    _memory_pet_repo = None
    _memory_order_repo = None
    _memory_user_repo = None


@lru_cache
def _cached_settings() -> Settings:
    """Return cached settings instance.

    Returns:
        Cached Settings instance.
    """
    return get_settings()


async def get_pet_service(
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> PetService:
    """Provide a PetService backed by the configured repository.

    Args:
        settings: Application settings.

    Returns:
        A configured PetService instance.
    """
    if settings.storage_mode == "memory":
        return PetService(get_memory_pet_repo())
    from app.db.session import get_db_session
    from app.repositories.postgres.pet import PostgresPetRepository

    # For postgres mode, we need to get a session — this is a simplified version
    # In real usage the session would be injected via Depends
    async for session in get_db_session():
        return PetService(PostgresPetRepository(session))
    raise RuntimeError("Could not obtain DB session")  # pragma: no cover


async def get_order_service(
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> OrderService:
    """Provide an OrderService backed by the configured repository.

    Args:
        settings: Application settings.

    Returns:
        A configured OrderService instance.
    """
    if settings.storage_mode == "memory":
        return OrderService(get_memory_order_repo())
    from app.db.session import get_db_session
    from app.repositories.postgres.order import PostgresOrderRepository

    async for session in get_db_session():
        return OrderService(PostgresOrderRepository(session))
    raise RuntimeError("Could not obtain DB session")  # pragma: no cover


async def get_user_service(
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> UserService:
    """Provide a UserService backed by the configured repository.

    Args:
        settings: Application settings.

    Returns:
        A configured UserService instance.
    """
    if settings.storage_mode == "memory":
        return UserService(get_memory_user_repo())
    from app.db.session import get_db_session
    from app.repositories.postgres.user import PostgresUserRepository

    async for session in get_db_session():
        return UserService(PostgresUserRepository(session))
    raise RuntimeError("Could not obtain DB session")  # pragma: no cover
