"""Store endpoints — /api/v1/store."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_order_service
from app.schemas.order import Order, OrderCreate
from app.services.order import OrderService

router = APIRouter(prefix="/store", tags=["store"])


@router.get("/inventory", response_model=dict[str, int])
async def get_inventory(
    service: Annotated[OrderService, Depends(get_order_service)],
) -> dict[str, int]:
    """Return pet inventories by status.

    Args:
        service: Injected OrderService.

    Returns:
        Dict mapping status to count of pets with that status.
    """
    return await service.get_inventory()


@router.post("/order", response_model=Order, status_code=200)
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
    return await service.place_order(order)


@router.get("/order/{order_id}", response_model=Order)
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
    return await service.get_order(order_id)


@router.delete("/order/{order_id}", status_code=200)
async def delete_order(
    order_id: int,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> dict[str, str]:
    """Delete purchase order by ID.

    Args:
        order_id: The order's unique identifier.
        service: Injected OrderService.

    Returns:
        Confirmation message.
    """
    await service.delete_order(order_id)
    return {"message": "Order deleted"}
