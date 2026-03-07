"""Performance benchmarks for pet operations."""

from __future__ import annotations

import asyncio

import pytest

from app.dependencies import get_memory_pet_repo, reset_memory_repos
from app.schemas.pet import PetCreate, PetStatus
from app.services.pet import PetService


@pytest.fixture(autouse=True)
def reset() -> None:
    """Reset in-memory repos before each benchmark."""
    reset_memory_repos()


def test_benchmark_create_pet(benchmark: object) -> None:
    """Benchmark pet creation in memory mode.

    Args:
        benchmark: pytest-benchmark fixture.
    """

    async def _create() -> None:
        service = PetService(get_memory_pet_repo())
        await service.add_pet(PetCreate(name="Bench", photoUrls=[], status=PetStatus.available))

    benchmark(lambda: asyncio.run(_create()))  # type: ignore[attr-defined]


def test_benchmark_list_by_status(benchmark: object) -> None:
    """Benchmark listing pets by status.

    Args:
        benchmark: pytest-benchmark fixture.
    """

    async def _setup() -> None:
        service = PetService(get_memory_pet_repo())
        for i in range(100):
            await service.add_pet(
                PetCreate(name=f"Pet{i}", photoUrls=[], status=PetStatus.available)
            )

    asyncio.run(_setup())

    async def _list() -> None:
        service = PetService(get_memory_pet_repo())
        await service.find_by_status("available")

    benchmark(lambda: asyncio.run(_list()))  # type: ignore[attr-defined]
