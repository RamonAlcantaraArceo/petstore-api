"""Order service — business logic layer delegating to the repository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, status

from app.repositories.base import OrderRepository
from app.schemas.order import Order, OrderCreate


class OrderService:
    """Service that encapsulates Order business logic.

    Args:
        repo: An OrderRepository implementation.
    """

    def __init__(
        self,
        repo: OrderRepository,
        commit: Callable[[], Awaitable[None]] | None = None,
        rollback: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the service with a repository.

        Args:
            repo: Repository implementation to delegate to.
            commit: Optional async transaction commit callback.
            rollback: Optional async transaction rollback callback.
        """
        self._repo = repo
        self._commit_callback = commit
        self._rollback_callback = rollback

    async def _commit(self) -> None:
        """Commit the current transaction when a callback is configured."""
        if self._commit_callback is not None:
            await self._commit_callback()

    async def _rollback(self) -> None:
        """Rollback the current transaction when a callback is configured."""
        if self._rollback_callback is not None:
            await self._rollback_callback()

    async def place_order(self, order: OrderCreate) -> Order:
        """Place a new order for a pet.

        Args:
            order: The order data to create.

        Returns:
            The created Order with assigned ID.

        Example:
            >>> service = OrderService(repo)
            >>> order = await service.place_order(OrderCreate(petId=1, quantity=1))
            >>> assert order.id is not None
        """
        try:
            created = await self._repo.create(order)
            await self._commit()
            return created
        except Exception:
            await self._rollback()
            raise

    async def get_order(self, order_id: int) -> Order:
        """Retrieve an order by ID.

        Args:
            order_id: The order's unique identifier.

        Returns:
            The order if found.

        Raises:
            HTTPException: 404 if order not found.
        """
        if order_id < 1 or order_id > 10:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        order = await self._repo.get(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def delete_order(self, order_id: int) -> None:
        """Cancel and delete an order.

        Args:
            order_id: The order's unique identifier.

        Raises:
            HTTPException: 400 if order_id is invalid, 404 if not found.
        """
        if order_id < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID")
        try:
            await self._repo.delete(order_id)
            await self._commit()
        except KeyError as exc:
            await self._rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            ) from exc
        except Exception:
            await self._rollback()
            raise

    async def get_inventory(self) -> dict[str, int]:
        """Return inventory counts grouped by pet status.

        Returns:
            Dict mapping status string to count.
        """
        return await self._repo.get_inventory()
