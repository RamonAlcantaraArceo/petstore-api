"""Unit tests for the fixture loader."""

from __future__ import annotations

from unittest.mock import AsyncMock

import allure
import pytest

from app.fixtures.datasets import FixtureDataset, OrderFixture, PetFixture, UserFixture, get_dataset
from app.fixtures.loader import apply_dataset
from app.schemas.order import Order, OrderStatus
from app.schemas.pet import Pet, PetStatus
from app.schemas.user import User

pytestmark = [allure.epic("Fixtures"), allure.feature("Loader")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pet(pet_id: int, name: str = "Fido") -> Pet:
    return Pet(id=pet_id, name=name, photoUrls=[], status=PetStatus.available)


def _make_order(order_id: int, pet_id: int) -> Order:
    return Order(id=order_id, pet_id=pet_id, quantity=1, status=OrderStatus.placed)


def _make_user(user_id: int, username: str = "johndoe") -> User:
    return User(id=user_id, username=username, email=f"{username}@example.com")


def _make_services(
    *,
    pet_side_effects: list[Pet] | None = None,
    order_side_effects: list[Order] | None = None,
    user_side_effects: list[User] | None = None,
) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    pet_service = AsyncMock()
    order_service = AsyncMock()
    user_service = AsyncMock()

    if pet_side_effects:
        pet_service.add_pet.side_effect = pet_side_effects
    if order_side_effects:
        order_service.place_order.side_effect = order_side_effects
    if user_side_effects:
        user_service.create_user.side_effect = user_side_effects

    return pet_service, order_service, user_service


# ---------------------------------------------------------------------------
# apply_dataset — empty dataset
# ---------------------------------------------------------------------------


@allure.story("Apply Dataset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_apply_empty_dataset_calls_no_services() -> None:
    """apply_dataset on an empty dataset makes no service calls."""
    dataset = get_dataset("empty")
    pet_service, order_service, user_service = _make_services()

    await apply_dataset(dataset, pet_service, order_service, user_service)

    pet_service.add_pet.assert_not_called()
    order_service.place_order.assert_not_called()
    user_service.create_user.assert_not_called()


# ---------------------------------------------------------------------------
# apply_dataset — pets
# ---------------------------------------------------------------------------


@allure.story("Apply Dataset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_apply_dataset_creates_all_pets() -> None:
    """apply_dataset creates one pet per PetFixture in the dataset."""
    dataset = FixtureDataset(
        name="test",
        description="test",
        pets=[
            PetFixture(name="Buddy", status=PetStatus.available),
            PetFixture(name="Max", status=PetStatus.pending),
        ],
    )
    pets = [_make_pet(1, "Buddy"), _make_pet(2, "Max")]
    pet_service, order_service, user_service = _make_services(pet_side_effects=pets)

    await apply_dataset(dataset, pet_service, order_service, user_service)

    assert pet_service.add_pet.call_count == 2


@allure.story("Apply Dataset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_apply_dataset_pet_create_uses_correct_fields() -> None:
    """PetCreate passed to the service matches the PetFixture fields."""
    from app.schemas.pet import Category, Tag

    category = Category(id=1, name="Dogs")
    tags = [Tag(id=1, name="friendly")]
    dataset = FixtureDataset(
        name="test",
        description="test",
        pets=[
            PetFixture(
                name="Rex",
                status=PetStatus.available,
                photo_urls=["http://example.com/rex.jpg"],
                category=category,
                tags=tags,
            )
        ],
    )
    pet_service, order_service, user_service = _make_services(
        pet_side_effects=[_make_pet(1, "Rex")]
    )

    await apply_dataset(dataset, pet_service, order_service, user_service)

    call_kwargs = pet_service.add_pet.call_args[0][0]
    assert call_kwargs.name == "Rex"
    assert call_kwargs.status == PetStatus.available
    assert call_kwargs.photo_urls == ["http://example.com/rex.jpg"]
    assert call_kwargs.category == category
    assert call_kwargs.tags == tags


# ---------------------------------------------------------------------------
# apply_dataset — orders
# ---------------------------------------------------------------------------


@allure.story("Apply Dataset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_apply_dataset_creates_orders_with_resolved_pet_ids() -> None:
    """Orders are created with the pet ID assigned during pet creation."""
    dataset = FixtureDataset(
        name="test",
        description="test",
        pets=[
            PetFixture(name="Goldie", status=PetStatus.sold),
        ],
        orders=[
            OrderFixture(pet_index=0, quantity=2, status=OrderStatus.delivered),
        ],
    )
    assigned_pet = _make_pet(42, "Goldie")
    assigned_pet = Pet(id=42, name="Goldie", photoUrls=[], status=PetStatus.sold)
    pet_service, order_service, user_service = _make_services(
        pet_side_effects=[assigned_pet],
        order_side_effects=[_make_order(1, 42)],
    )

    await apply_dataset(dataset, pet_service, order_service, user_service)

    order_service.place_order.assert_called_once()
    order_create = order_service.place_order.call_args[0][0]
    assert order_create.pet_id == 42
    assert order_create.quantity == 2
    assert order_create.status == OrderStatus.delivered


@allure.story("Apply Dataset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_apply_dataset_invalid_pet_index_raises_value_error() -> None:
    """ValueError is raised when an OrderFixture references an out-of-range pet_index."""
    dataset = FixtureDataset(
        name="test",
        description="test",
        pets=[PetFixture(name="A", status=PetStatus.available)],
        orders=[OrderFixture(pet_index=5)],  # index 5 doesn't exist
    )
    pet_service, order_service, user_service = _make_services(pet_side_effects=[_make_pet(1, "A")])

    with pytest.raises(ValueError, match="pet_index"):
        await apply_dataset(dataset, pet_service, order_service, user_service)


# ---------------------------------------------------------------------------
# apply_dataset — users
# ---------------------------------------------------------------------------


@allure.story("Apply Dataset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_apply_dataset_creates_all_users() -> None:
    """apply_dataset creates one user per UserFixture in the dataset."""
    dataset = FixtureDataset(
        name="test",
        description="test",
        users=[
            UserFixture(username="alice", email="alice@example.com"),
            UserFixture(username="bob", email="bob@example.com"),
        ],
    )
    users = [_make_user(1, "alice"), _make_user(2, "bob")]
    pet_service, order_service, user_service = _make_services(user_side_effects=users)

    await apply_dataset(dataset, pet_service, order_service, user_service)

    assert user_service.create_user.call_count == 2


@allure.story("Apply Dataset")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_apply_dataset_user_create_uses_correct_fields() -> None:
    """UserCreate passed to the service matches the UserFixture fields."""
    dataset = FixtureDataset(
        name="test",
        description="test",
        users=[
            UserFixture(
                username="alice",
                email="alice@example.com",
                first_name="Alice",
                last_name="Smith",
                phone="+1-555-000-0001",
                user_status=1,
                password="mypassword",
            )
        ],
    )
    pet_service, order_service, user_service = _make_services(
        user_side_effects=[_make_user(1, "alice")]
    )

    await apply_dataset(dataset, pet_service, order_service, user_service)

    call_kwargs = user_service.create_user.call_args[0][0]
    assert call_kwargs.username == "alice"
    assert call_kwargs.email == "alice@example.com"
    assert call_kwargs.first_name == "Alice"
    assert call_kwargs.last_name == "Smith"
    assert call_kwargs.phone == "+1-555-000-0001"
    assert call_kwargs.user_status == 1
    assert call_kwargs.password == "mypassword"


# ---------------------------------------------------------------------------
# seed_from_settings — memory mode
# ---------------------------------------------------------------------------


@allure.story("Seed From Settings")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_seed_from_settings_skips_when_seed_dataset_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """seed_from_settings is a no-op when seed_dataset is not set."""
    from app.config import Settings
    from app.fixtures.loader import seed_from_settings

    settings = Settings(api_key="test", storage_mode="memory", seed_dataset="")
    applied: list[str] = []

    import app.fixtures.loader as loader_mod

    original = loader_mod._seed_memory

    async def _mock_seed(dataset: FixtureDataset) -> None:
        applied.append(dataset.name)

    monkeypatch.setattr(loader_mod, "_seed_memory", _mock_seed)
    try:
        await seed_from_settings(settings)
    finally:
        loader_mod._seed_memory = original  # type: ignore[assignment]

    assert applied == []


@allure.story("Seed From Settings")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_seed_from_settings_calls_seed_memory_for_memory_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """seed_from_settings delegates to _seed_memory when storage_mode is 'memory'."""
    from app.config import Settings
    from app.fixtures.loader import seed_from_settings

    settings = Settings(api_key="test", storage_mode="memory", seed_dataset="basic")
    seeded: list[str] = []

    import app.fixtures.loader as loader_mod

    async def _mock_seed(dataset: FixtureDataset) -> None:
        seeded.append(dataset.name)

    monkeypatch.setattr(loader_mod, "_seed_memory", _mock_seed)

    await seed_from_settings(settings)

    assert seeded == ["basic"]


@allure.story("Seed From Settings")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_seed_from_settings_raises_for_unknown_dataset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """seed_from_settings propagates ValueError from get_dataset."""
    from app.config import Settings
    from app.fixtures.loader import seed_from_settings

    settings = Settings(api_key="test", storage_mode="memory", seed_dataset="does_not_exist")

    with pytest.raises(ValueError, match="Unknown fixture dataset"):
        await seed_from_settings(settings)


# ---------------------------------------------------------------------------
# Integration: memory repos receive seeded data
# ---------------------------------------------------------------------------


@allure.story("Memory Seeding Integration")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_seed_memory_populates_repos_with_basic_dataset() -> None:
    """_seed_memory actually inserts data into the in-memory repositories."""
    from app.dependencies import reset_memory_repos
    from app.fixtures.loader import _seed_memory

    reset_memory_repos()

    dataset = get_dataset("basic")
    await _seed_memory(dataset)

    from app.dependencies import get_memory_pet_repo, get_memory_user_repo
    from app.services.pet import PetService
    from app.services.user import UserService

    pet_service = PetService(get_memory_pet_repo())
    user_service = UserService(get_memory_user_repo())

    available_pets = await pet_service.find_by_status("available")
    assert len(available_pets) == len(dataset.pets)

    for user_fixture in dataset.users:
        user = await user_service.get_user(user_fixture.username)
        assert user.username == user_fixture.username

    reset_memory_repos()


@allure.story("Memory Seeding Integration")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_seed_memory_populates_repos_with_mixed_v1_dataset() -> None:
    """_seed_memory correctly seeds pets, orders, and users from mixed_v1."""
    from app.dependencies import reset_memory_repos
    from app.fixtures.loader import _seed_memory

    reset_memory_repos()

    dataset = get_dataset("mixed_v1")
    await _seed_memory(dataset)

    from app.dependencies import (
        get_memory_order_repo,
        get_memory_pet_repo,
        get_memory_user_repo,
    )
    from app.services.order import OrderService
    from app.services.pet import PetService
    from app.services.user import UserService

    pet_service = PetService(get_memory_pet_repo())
    order_service = OrderService(get_memory_order_repo())
    user_service = UserService(get_memory_user_repo())

    # Pets: all statuses present
    all_pets = await pet_service.find_by_status("available")
    assert len(all_pets) > 0

    # Orders: inventory should have entries
    inventory = await order_service.get_inventory()
    assert len(inventory) == len(dataset.orders)

    # Users: all seeded users retrievable
    for user_fixture in dataset.users:
        user = await user_service.get_user(user_fixture.username)
        assert user.username == user_fixture.username

    reset_memory_repos()
