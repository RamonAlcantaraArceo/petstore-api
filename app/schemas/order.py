"""Pydantic schemas for Order resources."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class OrderStatus(StrEnum):
    """Order fulfillment status."""

    placed = "placed"
    approved = "approved"
    delivered = "delivered"


class OrderBase(BaseModel):
    """Base order schema with shared fields.

    Attributes:
        pet_id: ID of the pet being ordered.
        quantity: Number of pets.
        ship_date: Expected ship date.
        status: Order status.
        complete: Whether the order is complete.
    """

    pet_id: int | None = None
    quantity: int | None = None
    ship_date: datetime | None = None
    status: OrderStatus | None = None
    complete: bool | None = False

    model_config = {"populate_by_name": True}


class OrderCreate(OrderBase):
    """Schema for creating a new order."""

    pass


class Order(OrderBase):
    """Full order schema including server-assigned fields.

    Attributes:
        id: Order identifier.
    """

    id: int | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}
