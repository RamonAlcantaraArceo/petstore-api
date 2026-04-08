"""Unit tests for OrderService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schemas.order import Order, OrderStatus
from app.services.order import OrderService
from tests.factories.order import OrderCreateFactory


def make_service(repo: AsyncMock) -> OrderService:
    """Build an OrderService around a mock repository.

    Args:
        repo: The mocked order repository.

    Returns:
        OrderService using the mock.
    """
    return OrderService(repo)


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
    """get_order raises HTTPException 404 when order is not found."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.get.return_value = None

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.get_order(5)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_order_raises_404_for_invalid_id() -> None:
    """get_order raises HTTPException 404 when order_id is out of range."""
    from fastapi import HTTPException

    repo = AsyncMock()

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.get_order(11)

    assert exc_info.value.status_code == 404


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
    """delete_order raises HTTPException 400 for id < 1."""
    from fastapi import HTTPException

    repo = AsyncMock()
    service = make_service(repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_order(0)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_order_raises_404_when_not_found() -> None:
    """delete_order raises HTTPException 404 when order not found."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.delete.side_effect = KeyError("Order not found")

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_order(1)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_inventory_delegates_to_repo() -> None:
    """get_inventory calls repository get_inventory."""
    repo = AsyncMock()
    repo.get_inventory.return_value = {"placed": 3, "delivered": 10}

    service = make_service(repo)
    result = await service.get_inventory()

    assert result["placed"] == 3
    assert result["delivered"] == 10


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
