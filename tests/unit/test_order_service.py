"""Unit tests for OrderService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from petstore_core.errors import NotFoundError, ValidationError
from petstore_core.schemas.order import Order, OrderStatus
from petstore_core.services.order import OrderService

from tests.factories.order import OrderCreateFactory


def make_service(
    repo: AsyncMock, commit: AsyncMock | None = None, rollback: AsyncMock | None = None
) -> OrderService:
    return OrderService(repo, commit=commit, rollback=rollback)


@pytest.mark.asyncio
async def test_place_order_delegates_to_repo() -> None:
    """place_order delegates creation to the repository."""
    repo = AsyncMock()
    order_data = OrderCreateFactory()
    expected = Order(id=1, pet_id=order_data.pet_id, quantity=order_data.quantity)
    repo.create.return_value = expected

    service = make_service(repo)
    result = await service.place_order(order_data)

    repo.create.assert_called_once_with(order_data)
    assert result.id == 1


@pytest.mark.asyncio
async def test_get_order_returns_order() -> None:
    """get_order returns the order when found."""
    repo = AsyncMock()
    order = Order(id=1, pet_id=2, quantity=1, status=OrderStatus.placed)
    repo.get.return_value = order

    service = make_service(repo)
    result = await service.get_order(1)

    assert result.id == 1


@pytest.mark.asyncio
async def test_get_order_raises_404_when_not_found() -> None:
    """get_order raises NotFoundError when order is not found."""

    repo = AsyncMock()
    repo.get.return_value = None

    service = make_service(repo)
    with pytest.raises(NotFoundError, match="Order not found"):
        await service.get_order(5)


@pytest.mark.asyncio
async def test_get_order_raises_400_for_id_less_than_1() -> None:
    """get_order raises ValidationError when order_id < 1."""

    repo = AsyncMock()
    service = make_service(repo)
    with pytest.raises(ValidationError, match="Invalid order ID"):
        await service.get_order(0)


@pytest.mark.asyncio
async def test_get_order_raises_404_for_id_greater_than_10() -> None:
    """get_order raises NotFoundError when order_id > 10 and no record exists."""

    repo = AsyncMock()
    repo.get.return_value = None
    service = make_service(repo)
    with pytest.raises(NotFoundError, match="Order not found"):
        await service.get_order(11)


@pytest.mark.asyncio
async def test_delete_order_calls_repo() -> None:
    """delete_order calls repository delete."""
    repo = AsyncMock()
    repo.delete.return_value = None

    service = make_service(repo)
    await service.delete_order(1)

    repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_order_raises_400_for_invalid_id() -> None:
    """delete_order raises ValidationError for id < 1."""

    repo = AsyncMock()
    service = make_service(repo)

    with pytest.raises(ValidationError, match="Invalid order ID"):
        await service.delete_order(0)


@pytest.mark.asyncio
async def test_delete_order_raises_404_when_not_found() -> None:
    """delete_order raises NotFoundError when order not found."""

    repo = AsyncMock()
    repo.delete.side_effect = KeyError("Order not found")

    service = make_service(repo)
    with pytest.raises(NotFoundError, match="Order not found"):
        await service.delete_order(1)


@pytest.mark.asyncio
async def test_get_inventory_delegates_to_repo() -> None:
    """get_inventory calls repository get_inventory."""
    repo = AsyncMock()
    expected = [Order(id=1, pet_id=1, quantity=2), Order(id=2, pet_id=3, quantity=1)]
    repo.get_inventory.return_value = expected

    service = make_service(repo)
    result = await service.get_inventory()

    assert result == expected


@pytest.mark.asyncio
async def test_place_order_commits_when_callback_is_configured() -> None:
    """place_order calls commit callback after successful write."""
    repo = AsyncMock()
    order_data = OrderCreateFactory()
    expected = Order(id=1, pet_id=order_data.pet_id, quantity=order_data.quantity)
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()

    service = OrderService(repo, commit=commit, rollback=rollback)
    await service.place_order(order_data)

    commit.assert_awaited_once()
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_delete_order_rolls_back_on_unexpected_error() -> None:
    """delete_order rolls back and re-raises for non-domain repository errors."""
    repo = AsyncMock()
    repo.delete.side_effect = RuntimeError("db down")
    commit = AsyncMock()
    rollback = AsyncMock()

    service = OrderService(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db down"):
        await service.delete_order(1)

    commit.assert_not_called()
    rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_place_order_successful_creation():
    repo = AsyncMock()
    order_data = OrderCreateFactory()
    expected = Order(
        id=1,
        pet_id=order_data.pet_id,
        quantity=order_data.quantity,
        ship_date=None,
        status=None,
        complete=False,
    )
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    result = await service.place_order(order_data)
    repo.create.assert_called_once_with(order_data)
    commit.assert_awaited_once()
    rollback.assert_not_called()
    assert result == expected


@pytest.mark.asyncio
async def test_place_order_rolls_back_and_reraises_on_exception():
    repo = AsyncMock()
    order_data = OrderCreateFactory()
    repo.create.side_effect = RuntimeError("db error")
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db error"):
        await service.place_order(order_data)
    rollback.assert_awaited_once()
    commit.assert_not_called()


@pytest.mark.asyncio
async def test_place_order_does_not_call_rollback_on_success():
    repo = AsyncMock()
    order_data = OrderCreateFactory()
    expected = Order(
        id=1,
        pet_id=order_data.pet_id,
        quantity=order_data.quantity,
        ship_date=None,
        status=None,
        complete=False,
    )
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.place_order(order_data)
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_place_order_calls_commit_on_success():
    repo = AsyncMock()
    order_data = OrderCreateFactory()
    expected = Order(
        id=1,
        pet_id=order_data.pet_id,
        quantity=order_data.quantity,
        ship_date=None,
        status=None,
        complete=False,
    )
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = make_service(repo, commit=commit, rollback=rollback)
    await service.place_order(order_data)
    commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_place_order_calls_repo_create():
    repo = AsyncMock()
    order_data = OrderCreateFactory()
    expected = Order(
        id=1,
        pet_id=order_data.pet_id,
        quantity=order_data.quantity,
        ship_date=None,
        status=None,
        complete=False,
    )
    repo.create.return_value = expected
    service = make_service(repo)
    await service.place_order(order_data)
    repo.create.assert_called_once_with(order_data)
