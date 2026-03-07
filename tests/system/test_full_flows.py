"""System tests — multi-step business workflow end-to-end."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_pet_lifecycle(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """Full lifecycle: create user, add pet, place order, verify inventory, delete all."""
    # 1. Create a user
    user_resp = await app_client.post(
        "/api/v1/user",
        json={"username": "workflow_user", "email": "workflow@example.com"},
        headers=api_key_header,
    )
    assert user_resp.status_code == 200
    username = user_resp.json()["username"]

    # 2. Add a pet
    pet_resp = await app_client.post(
        "/api/v1/pet",
        json={"name": "Workflow Pet", "photoUrls": [], "status": "available"},
        headers=api_key_header,
    )
    assert pet_resp.status_code == 200
    pet_id = pet_resp.json()["id"]

    # 3. Verify pet is findable by status
    find_resp = await app_client.get(
        "/api/v1/pet/findByStatus?status=available", headers=api_key_header
    )
    assert any(p["id"] == pet_id for p in find_resp.json())

    # 4. Place an order
    order_resp = await app_client.post(
        "/api/v1/store/order",
        json={"petId": pet_id, "quantity": 1, "status": "placed", "complete": False},
        headers=api_key_header,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    # 5. Verify inventory
    inv_resp = await app_client.get("/api/v1/store/inventory", headers=api_key_header)
    assert inv_resp.status_code == 200

    # 6. Update pet status to sold
    update_resp = await app_client.put(
        "/api/v1/pet",
        json={"id": pet_id, "name": "Workflow Pet", "photoUrls": [], "status": "sold"},
        headers=api_key_header,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "sold"

    # 7. Delete the order
    del_order_resp = await app_client.delete(
        f"/api/v1/store/order/{order_id}", headers=api_key_header
    )
    assert del_order_resp.status_code == 200

    # 8. Delete the pet
    del_pet_resp = await app_client.delete(f"/api/v1/pet/{pet_id}", headers=api_key_header)
    assert del_pet_resp.status_code == 200

    # 9. Delete the user
    del_user_resp = await app_client.delete(f"/api/v1/user/{username}", headers=api_key_header)
    assert del_user_resp.status_code == 200
