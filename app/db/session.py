"""Async engine and session factory; selects implementation via config."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings

_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    """Initialise the async SQLAlchemy engine and session factory.

    Called once at application startup when storage_mode is not "memory".

    Args:
        settings: Application settings containing the database URL and pool config.
    """
    global _session_factory
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        echo=settings.debug,
    )
    _session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
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
