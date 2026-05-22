"""Async fixture loader — seeds a storage backend from a named dataset.

Usage (memory mode)
-------------------
Set ``SEED_DATASET=basic`` (or any other dataset name) in the environment
before starting the service.  The application lifespan will call
:func:`seed_from_settings` automatically.

Usage (script)
--------------
See ``scripts/load_fixtures.py`` for a CLI wrapper around this module.
"""

from __future__ import annotations

import structlog

from app.fixtures.datasets import FixtureDataset, get_dataset
from app.schemas.order import OrderCreate
from app.schemas.pet import PetCreate
from app.schemas.user import UserCreate
from app.services.order import OrderService
from app.services.pet import PetService
from app.services.user import UserService

logger = structlog.get_logger(__name__)


async def apply_dataset(
    dataset: FixtureDataset,
    pet_service: PetService,
    order_service: OrderService,
    user_service: UserService,
) -> None:
    """Seed a storage backend with the entities in *dataset*.

    Pets are created first so that their assigned IDs can be used when
    creating orders.  Users are created last.

    Args:
        dataset: The fixture dataset to apply.
        pet_service: Service used to persist pets.
        order_service: Service used to persist orders.
        user_service: Service used to persist users.
    """
    log = logger.bind(dataset=dataset.name)

    created_pet_ids: list[int] = []
    for pet_fixture in dataset.pets:
        pet = await pet_service.add_pet(
            PetCreate(
                name=pet_fixture.name,
                photo_urls=pet_fixture.photo_urls,
                status=pet_fixture.status,
                category=pet_fixture.category,
                tags=pet_fixture.tags,
            )
        )
        pet_id = pet.id or 0
        created_pet_ids.append(pet_id)
        log.info("seeded pet", pet_id=pet_id, name=pet.name, status=pet.status)

    for order_fixture in dataset.orders:
        if order_fixture.pet_index >= len(created_pet_ids):
            raise ValueError(
                f"Order fixture references pet_index={order_fixture.pet_index} "
                f"but only {len(created_pet_ids)} pet(s) were created."
            )
        pet_id = created_pet_ids[order_fixture.pet_index]
        order = await order_service.place_order(
            OrderCreate(
                pet_id=pet_id,
                quantity=order_fixture.quantity,
                status=order_fixture.status,
                ship_date=order_fixture.ship_date,
                complete=order_fixture.complete,
            )
        )
        log.info(
            "seeded order",
            order_id=order.id,
            pet_id=pet_id,
            status=order.status,
        )

    for user_fixture in dataset.users:
        user = await user_service.create_user(
            UserCreate(
                username=user_fixture.username,
                email=user_fixture.email,
                first_name=user_fixture.first_name,
                last_name=user_fixture.last_name,
                phone=user_fixture.phone,
                user_status=user_fixture.user_status,
                password=user_fixture.password,
            )
        )
        log.info("seeded user", user_id=user.id, username=user.username)


async def seed_from_settings(settings: object) -> None:
    """Load a fixture dataset according to application settings.

    Reads ``settings.seed_dataset`` to determine which dataset to apply,
    then picks the correct repository implementation based on
    ``settings.storage_mode``.

    Args:
        settings: Application :class:`~app.config.Settings` instance.

    Raises:
        ValueError: When the dataset name is not recognised.
    """
    from app.config import Settings

    assert isinstance(settings, Settings)

    if not settings.seed_dataset:
        return

    dataset = get_dataset(settings.seed_dataset)

    if not dataset.pets and not dataset.orders and not dataset.users:
        logger.info("seed_dataset is 'empty' — skipping seeding", dataset=dataset.name)
        return

    logger.info(
        "seeding storage",
        dataset=dataset.name,
        storage_mode=settings.storage_mode,
    )

    if settings.storage_mode == "memory":
        await _seed_memory(dataset)
    else:
        await _seed_postgres(dataset)


async def _seed_memory(dataset: FixtureDataset) -> None:
    """Seed the in-memory repositories.

    Args:
        dataset: Dataset to apply.
    """
    from app.dependencies import (
        get_memory_order_repo,
        get_memory_pet_repo,
        get_memory_user_repo,
    )

    pet_service = PetService(get_memory_pet_repo())
    order_service = OrderService(get_memory_order_repo())
    user_service = UserService(get_memory_user_repo())
    await apply_dataset(dataset, pet_service, order_service, user_service)


async def _seed_postgres(dataset: FixtureDataset) -> None:
    """Seed a PostgreSQL database using a short-lived session.

    Args:
        dataset: Dataset to apply.
    """
    from app.db.session import get_session_factory
    from app.repositories.postgres.order import PostgresOrderRepository
    from app.repositories.postgres.pet import PostgresPetRepository
    from app.repositories.postgres.user import PostgresUserRepository

    session_factory = get_session_factory()
    async with session_factory() as session:
        pet_service = PetService(
            PostgresPetRepository(session),
            commit=session.commit,
            rollback=session.rollback,
        )
        order_service = OrderService(
            PostgresOrderRepository(session),
            commit=session.commit,
            rollback=session.rollback,
        )
        user_service = UserService(
            PostgresUserRepository(session),
            commit=session.commit,
            rollback=session.rollback,
        )
        await apply_dataset(dataset, pet_service, order_service, user_service)
