"""SQLAlchemy ORM model for Order."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer
from sqlalchemy.orm import DeclarativeBase


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

    id = Column(Integer, primary_key=True, autoincrement=True)
    pet_id = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    ship_date = Column(DateTime(timezone=True), nullable=True)
    status: Column[str] = Column(
        Enum("placed", "approved", "delivered", name="order_status"),
        default="placed",
        nullable=True,
    )
    complete = Column(Boolean, default=False, nullable=True)
