"""SQLAlchemy ORM model for Order."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Enum, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class OrderModel(Base):
    """SQLAlchemy ORM model representing a store order.

    Attributes:
        id: Primary key.
        pet_id: ID of the pet being ordered.
        quantity: Number of pets.
        ship_date: Expected ship date.
        status: Order status.
        complete: Whether order is complete.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ship_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(
        Enum("placed", "approved", "delivered", name="order_status"),
        default="placed",
        nullable=True,
    )
    complete: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)

