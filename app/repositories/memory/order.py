"""In-memory Order repository implementation."""

from __future__ import annotations

import asyncio

from app.schemas.order import Order, OrderCreate


class MemoryOrderRepository:
    """Thread-safe in-memory Order repository backed by a dict.

    State is held in-process and lost on restart.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory order store."""
        self._store: dict[int, Order] = {}
        self._counter: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, order_id: int) -> Order | None:
        """Retrieve an order by ID.

        Args:
            order_id: The order's unique identifier.

        Returns:
            The order if found, else None.
        """
        return self._store.get(order_id)

    async def create(self, order: OrderCreate) -> Order:
        """Persist a new order.

        Args:
            order: Order data to create.

        Returns:
            The created order with assigned ID.
        """
        async with self._lock:
            self._counter += 1
            new_id = self._counter
            new_order = Order(
                id=new_id,
                pet_id=order.pet_id,
                quantity=order.quantity,
                ship_date=order.ship_date,
                status=order.status,
                complete=order.complete,
            )
            self._store[new_id] = new_order
            return new_order

    async def delete(self, order_id: int) -> None:
        """Delete an order by ID.

        Args:
            order_id: The order's unique identifier.

        Raises:
            KeyError: If order not found.
        """
        async with self._lock:
            if order_id not in self._store:
                raise KeyError(f"Order {order_id} not found")
            del self._store[order_id]

    async def get_inventory(self) -> dict[str, int]:
        """Return inventory counts grouped by order status.

        Returns:
            Dict mapping status string to count.
        """
        counts: dict[str, int] = {}
        for order in self._store.values():
            if order.status:
                key = order.status.value
                counts[key] = counts.get(key, 0) + 1
        return counts
