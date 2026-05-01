"""Async engine and session factory; selects implementation via config."""

from __future__ import annotations

from collections.abc import AsyncIterator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.models.order import Base as OrderBase
from app.models.pet import Base as PetBase
from app.models.user import Base as UserBase

_session_factory: async_sessionmaker[AsyncSession] | None = None
_engine: AsyncEngine | None = None
_logger = structlog.get_logger(__name__)


def init_db(settings: Settings) -> None:
    """Initialise the async SQLAlchemy engine and session factory.

    Called once at application startup when storage_mode is not "memory".

    Args:
        settings: Application settings containing the database URL and pool config.
    """
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        connect_args=settings.async_database_connect_args,
        echo=settings.debug,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def ensure_db_schema() -> None:
    """Create required tables when running in DB-backed mode.

    Raises:
        RuntimeError: If the engine has not been initialised.
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_db() first.")

    async with _engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                SELECT
                    current_database(),
                    current_user,
                    inet_server_addr()::text,
                    inet_server_port()
                """
            )
        )
        database, user, server_address, server_port = result.one()
        _logger.info(
            "db_connection_established",
            database=database,
            user=user,
            server_address=server_address,
            server_port=server_port,
        )

        await conn.run_sync(PetBase.metadata.create_all)
        await conn.run_sync(OrderBase.metadata.create_all)
        await conn.run_sync(UserBase.metadata.create_all)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return initialised async session factory.

    Returns:
        Initialised async sessionmaker instance.

    Raises:
        RuntimeError: If the session factory has not been initialised.
    """
    if _session_factory is None:
        raise RuntimeError("Database session factory not initialised. Call init_db() first.")
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for use in FastAPI dependencies.

    Yields:
        An open AsyncSession that is committed on success and rolled back
        on exception.

    Raises:
        RuntimeError: If the session factory has not been initialised.
    """
    if _session_factory is None:
        raise RuntimeError("Database session factory not initialised. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
