"""Store endpoints — /api/v1/store."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from petstore_core.schemas.order import Order, OrderCreate
from petstore_core.services.order import OrderService

from app.api.v1.error_mapping import map_domain_errors
from app.dependencies import get_order_service

router = APIRouter(prefix="/store", tags=["store"])


@router.get("/inventory", response_model=list[Order], operation_id="get_inventory")
async def get_inventory(
    service: Annotated[OrderService, Depends(get_order_service)],
) -> list[Order]:
    """Return all orders in the store.

    Args:
        service: Injected OrderService.

    Returns:
        List of all orders.
    """
    return await map_domain_errors(service.get_inventory())


@router.post("/order", response_model=Order, status_code=200, operation_id="place_order")
async def place_order(
    order: OrderCreate,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order:
    """Place an order for a pet.

    Args:
        order: Order data from request body.
        service: Injected OrderService.

    Returns:
        The placed order.
    """
    return await map_domain_errors(service.place_order(order))


@router.get("/order/{order_id}", response_model=Order, operation_id="get_order_by_id")
async def get_order_by_id(
    order_id: int,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order:
    """Find purchase order by ID.

    Args:
        order_id: The order's unique identifier (1–10).
        service: Injected OrderService.

    Returns:
        The order with the given ID.
    """
    return await map_domain_errors(service.get_order(order_id))


@router.delete("/order/{order_id}", status_code=204, operation_id="delete_order")
async def delete_order(
    order_id: int,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> None:
    """Delete purchase order by ID.

    Args:
        order_id: The order's unique identifier.
        service: Injected OrderService.

    Returns:
        Confirmation message.
    """
    await map_domain_errors(service.delete_order(order_id))
    return
