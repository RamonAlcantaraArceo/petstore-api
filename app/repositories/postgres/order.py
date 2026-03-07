"""Async SQLAlchemy Order repository implementation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import OrderModel
from app.schemas.order import Order, OrderCreate, OrderStatus


def _model_to_schema(model: OrderModel) -> Order:
    """Convert an OrderModel ORM instance to an Order schema.

    Args:
        model: The SQLAlchemy ORM order model.

    Returns:
        An Order Pydantic schema instance.
    """
    id_val: Any = model.id
    pet_id_val: Any = model.pet_id
    quantity_val: Any = model.quantity
    ship_date_val: Any = model.ship_date
    status_val: Any = model.status
    complete_val: Any = model.complete
    return Order(
        id=id_val,
        pet_id=pet_id_val,
        quantity=quantity_val,
        ship_date=ship_date_val,
        status=OrderStatus(status_val) if status_val else None,
        complete=complete_val,
    )


class PostgresOrderRepository:
    """Async SQLAlchemy Order repository implementation.

    Args:
        session: An async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: Async SQLAlchemy session to use for queries.
        """
        self._session = session

    async def get(self, order_id: int) -> Order | None:
        """Retrieve an order by ID.

        Args:
            order_id: The order's unique identifier.

        Returns:
            The order if found, else None.
        """
        result = await self._session.execute(select(OrderModel).where(OrderModel.id == order_id))
        model = result.scalar_one_or_none()
        return _model_to_schema(model) if model else None

    async def create(self, order: OrderCreate) -> Order:
        """Persist a new order.

        Args:
            order: Order data to create.

        Returns:
            The created order with assigned ID.
        """
        model = OrderModel(
            pet_id=order.pet_id,
            quantity=order.quantity,
            ship_date=order.ship_date,
            status=order.status.value if order.status else None,
            complete=order.complete,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _model_to_schema(model)

    async def delete(self, order_id: int) -> None:
        """Delete an order by ID.

        Args:
            order_id: The order's unique identifier.

        Raises:
            KeyError: If order not found.
        """
        result = await self._session.execute(select(OrderModel).where(OrderModel.id == order_id))
        model = result.scalar_one_or_none()
        if not model:
            raise KeyError(f"Order {order_id} not found")
        await self._session.delete(model)
        await self._session.flush()

    async def get_inventory(self) -> dict[str, int]:
        """Return inventory counts grouped by order status.

        Returns:
            Dict mapping status string to count.
        """
        result = await self._session.execute(select(OrderModel))
        counts: dict[str, int] = {}
        for model in result.scalars().all():
            status_val: Any = model.status
            if status_val:
                counts[str(status_val)] = counts.get(str(status_val), 0) + 1
        return counts
