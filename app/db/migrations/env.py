"""Alembic environment configuration."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context

# Load app config
from petstore_core.config import get_settings
from petstore_core.models.order import Base as OrderBase
from petstore_core.models.pet import Base as PetBase
from petstore_core.models.user import Base as UserBase
from sqlalchemy.ext.asyncio import create_async_engine

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Combine all metadata
target_metadata = [PetBase.metadata, OrderBase.metadata, UserBase.metadata]


def _get_migration_db_config() -> tuple[str, dict[str, Any]]:
    """Return the resolved async DB URL and connect args for migrations."""
    settings = get_settings()
    connect_args = dict(getattr(settings, "async_database_connect_args", {}) or {})
    return settings.async_database_url, connect_args


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    """
    url, _ = _get_migration_db_config()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    """Run migrations with an active connection.

    Args:
        connection: The active database connection.
    """
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    database_url, connect_args = _get_migration_db_config()
    engine = create_async_engine(
        database_url,
        connect_args=connect_args,
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
