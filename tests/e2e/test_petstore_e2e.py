"""End-to-end tests against a live staging environment."""

from __future__ import annotations

import allure
import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def add_allure_layer() -> None:
    """Add a default 'e2e' layer label to all tests in this module."""
    allure.dynamic.label("layer", "e2e")


@pytest.mark.asyncio
@pytest.mark.remote_only
@pytest.mark.backend_agnostic
@pytest.mark.parametrize("path", ["/health", "/api/v1/health"])
async def test_e2e_health(remote_client: AsyncClient, path: str) -> None:
    """Smoke test: health returns 200 from both routes.

    Args:
        remote_client: Client pointing at the live service.
    """
    response = await remote_client.get(path)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
@pytest.mark.remote_only
@pytest.mark.backend_agnostic
async def test_e2e_pet_crud(
    remote_client: AsyncClient, remote_api_key_header: dict[str, str]
) -> None:
    """E2E CRUD: create, update through statuses, verify, and delete a pet.

    Args:
        remote_client: Client pointing at the live service.
    """
    create_resp = await remote_client.post(
        "/api/v1/pet",
        json={"name": "E2E Pet", "photoUrls": [], "status": "available"},
        headers=remote_api_key_header,
    )
    assert create_resp.status_code == 200
    created_pet = create_resp.json()
    pet_id = created_pet["id"]
    assert created_pet["status"] == "available"

    get_resp = await remote_client.get(f"/api/v1/pet/{pet_id}", headers=remote_api_key_header)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == pet_id
    assert get_resp.json()["status"] == "available"

    for status in ["pending", "sold"]:
        update_resp = await remote_client.put(
            "/api/v1/pet",
            json={
                "id": pet_id,
                "name": "E2E Pet",
                "photoUrls": [],
                "status": status,
            },
            headers=remote_api_key_header,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["id"] == pet_id
        assert update_resp.json()["status"] == status

        verify_get_resp = await remote_client.get(
            f"/api/v1/pet/{pet_id}", headers=remote_api_key_header
        )
        assert verify_get_resp.status_code == 200
        assert verify_get_resp.json()["status"] == status

        find_by_status_resp = await remote_client.get(
            f"/api/v1/pet/findByStatus?status={status}",
            headers=remote_api_key_header,
        )
        assert find_by_status_resp.status_code == 200
        assert any(pet["id"] == pet_id for pet in find_by_status_resp.json())

    delete_resp = await remote_client.delete(f"/api/v1/pet/{pet_id}", headers=remote_api_key_header)
    assert delete_resp.status_code == 204

    get_after_delete_resp = await remote_client.get(
        f"/api/v1/pet/{pet_id}", headers=remote_api_key_header
    )
    assert get_after_delete_resp.status_code == 404
