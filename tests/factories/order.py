"""Factory classes for generating test Order data."""

from __future__ import annotations

from datetime import UTC, datetime

import factory

from app.schemas.order import OrderCreate, OrderStatus


class OrderCreateFactory(factory.Factory):
    """Factory for generating OrderCreate instances.

    Example:
        >>> order = OrderCreateFactory()
        >>> assert order.pet_id is not None
    """

    class Meta:
        """Factory metadata."""

        model = OrderCreate

    pet_id = factory.Sequence(lambda n: n + 1)
    quantity = 1
    ship_date = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    status = OrderStatus.placed
    complete = False
