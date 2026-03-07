"""Integration tests for Store API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_inventory(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/store/inventory returns a dict."""
    response = await app_client.get("/api/v1/store/inventory", headers=api_key_header)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_place_order(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """POST /api/v1/store/order places an order."""
    payload = {"petId": 1, "quantity": 2, "status": "placed", "complete": False}
    response = await app_client.post("/api/v1/store/order", json=payload, headers=api_key_header)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["quantity"] == 2


@pytest.mark.asyncio
async def test_get_order_by_id(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/store/order/{id} returns the order."""
    create_resp = await app_client.post(
        "/api/v1/store/order",
        json={"petId": 1, "quantity": 1, "status": "placed", "complete": False},
        headers=api_key_header,
    )
    order_id = create_resp.json()["id"]

    response = await app_client.get(f"/api/v1/store/order/{order_id}", headers=api_key_header)
    assert response.status_code == 200
    assert response.json()["id"] == order_id


@pytest.mark.asyncio
async def test_delete_order(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """DELETE /api/v1/store/order/{id} removes the order."""
    create_resp = await app_client.post(
        "/api/v1/store/order",
        json={"petId": 2, "quantity": 1, "status": "placed", "complete": False},
        headers=api_key_header,
    )
    order_id = create_resp.json()["id"]

    del_resp = await app_client.delete(f"/api/v1/store/order/{order_id}", headers=api_key_header)
    assert del_resp.status_code == 200

    get_resp = await app_client.get(f"/api/v1/store/order/{order_id}", headers=api_key_header)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_order_not_found(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/store/order/{id} returns 404 for missing order."""
    response = await app_client.get("/api/v1/store/order/5", headers=api_key_header)
    assert response.status_code == 404
