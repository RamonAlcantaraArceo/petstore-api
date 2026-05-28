"""Compatibility wrapper for order schemas from petstore_core."""

from petstore_core.schemas.order import Order, OrderBase, OrderCreate, OrderStatus

__all__ = ["OrderStatus", "OrderBase", "OrderCreate", "Order"]
