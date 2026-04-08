"""FastAPI dependency injection — db session, auth, config, and service factories."""

from __future__ import annotations

from collections.abc import AsyncIterator
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
) -> AsyncIterator[PetService]:
    """Provide a PetService backed by the configured repository.

    Args:
        settings: Application settings.

    Returns:
        A configured PetService instance.
    """
    if settings.storage_mode == "memory":
        yield PetService(get_memory_pet_repo())
        return
    from app.db.session import get_session_factory
    from app.repositories.postgres.pet import PostgresPetRepository

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield PetService(
            PostgresPetRepository(session),
            commit=session.commit,
            rollback=session.rollback,
        )


async def get_order_service(
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> AsyncIterator[OrderService]:
    """Provide an OrderService backed by the configured repository.

    Args:
        settings: Application settings.

    Returns:
        A configured OrderService instance.
    """
    if settings.storage_mode == "memory":
        yield OrderService(get_memory_order_repo())
        return
    from app.db.session import get_session_factory
    from app.repositories.postgres.order import PostgresOrderRepository

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield OrderService(
            PostgresOrderRepository(session),
            commit=session.commit,
            rollback=session.rollback,
        )


async def get_user_service(
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> AsyncIterator[UserService]:
    """Provide a UserService backed by the configured repository.

    Args:
        settings: Application settings.

    Returns:
        A configured UserService instance.
    """
    if settings.storage_mode == "memory":
        yield UserService(get_memory_user_repo())
        return
    from app.db.session import get_session_factory
    from app.repositories.postgres.user import PostgresUserRepository

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield UserService(
            PostgresUserRepository(session),
            commit=session.commit,
            rollback=session.rollback,
        )
