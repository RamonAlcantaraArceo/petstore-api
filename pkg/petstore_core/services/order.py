"""Order service — business logic layer delegating to the repository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from petstore_core.errors import NotFoundError, ValidationError
from petstore_core.repositories.base import OrderRepository
from petstore_core.schemas.order import Order, OrderCreate


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
            ValidationError: If order_id is invalid.
            NotFoundError: If order not found.
        """
        if order_id < 1:
            raise ValidationError("Invalid order ID")
        order = await self._repo.get(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        return order

    async def delete_order(self, order_id: int) -> None:
        """Cancel and delete an order.

        Args:
            order_id: The order's unique identifier.

        Raises:
            ValidationError: If order_id is invalid.
            NotFoundError: If order not found.
        """
        if order_id < 1:
            raise ValidationError("Invalid order ID")
        try:
            await self._repo.delete(order_id)
            await self._commit()
        except KeyError as exc:
            await self._rollback()
            raise NotFoundError("Order not found") from exc
        except Exception:
            await self._rollback()
            raise

    async def get_inventory(self) -> list[Order]:
        """Return all orders in the store.

        Returns:
            List of all orders.
        """
        return await self._repo.get_inventory()
