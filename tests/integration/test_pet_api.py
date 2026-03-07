"""Integration tests for Pet API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.factories.pet import PetCreateFactory


@pytest.mark.asyncio
async def test_health_check(app_client: AsyncClient) -> None:
    """GET /health returns 200 with status ok."""
    response = await app_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "memory"


@pytest.mark.asyncio
async def test_add_pet(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """POST /api/v1/pet creates a pet and returns it."""
    pet_data = PetCreateFactory()
    payload = {
        "name": pet_data.name,
        "photoUrls": pet_data.photo_urls,
        "status": "available",
    }
    response = await app_client.post("/api/v1/pet", json=payload, headers=api_key_header)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == pet_data.name
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_get_pet_by_id(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/pet/{id} returns the pet."""
    # Create first
    payload = {"name": "Buddy", "photoUrls": [], "status": "available"}
    create_resp = await app_client.post("/api/v1/pet", json=payload, headers=api_key_header)
    pet_id = create_resp.json()["id"]

    response = await app_client.get(f"/api/v1/pet/{pet_id}", headers=api_key_header)
    assert response.status_code == 200
    assert response.json()["id"] == pet_id


@pytest.mark.asyncio
async def test_get_pet_not_found(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/pet/{id} returns 404 when not found."""
    response = await app_client.get("/api/v1/pet/99999", headers=api_key_header)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_pet(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """PUT /api/v1/pet updates the pet."""
    create_resp = await app_client.post(
        "/api/v1/pet",
        json={"name": "Rex", "photoUrls": [], "status": "available"},
        headers=api_key_header,
    )
    pet_id = create_resp.json()["id"]

    update_resp = await app_client.put(
        "/api/v1/pet",
        json={"id": pet_id, "name": "Max", "photoUrls": [], "status": "pending"},
        headers=api_key_header,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Max"


@pytest.mark.asyncio
async def test_delete_pet(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """DELETE /api/v1/pet/{id} removes the pet."""
    create_resp = await app_client.post(
        "/api/v1/pet",
        json={"name": "Goldie", "photoUrls": [], "status": "available"},
        headers=api_key_header,
    )
    pet_id = create_resp.json()["id"]

    delete_resp = await app_client.delete(f"/api/v1/pet/{pet_id}", headers=api_key_header)
    assert delete_resp.status_code == 200

    get_resp = await app_client.get(f"/api/v1/pet/{pet_id}", headers=api_key_header)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_find_by_status(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/pet/findByStatus returns matching pets."""
    await app_client.post(
        "/api/v1/pet",
        json={"name": "Available Pet", "photoUrls": [], "status": "available"},
        headers=api_key_header,
    )
    response = await app_client.get(
        "/api/v1/pet/findByStatus?status=available", headers=api_key_header
    )
    assert response.status_code == 200
    pets = response.json()
    assert all(p["status"] == "available" for p in pets)


@pytest.mark.asyncio
async def test_correlation_id_in_response(
    app_client: AsyncClient,
    api_key_header: dict[str, str],
    correlation_id_header: dict[str, str],
) -> None:
    """Response contains X-Correlation-ID header."""
    headers = {**api_key_header, **correlation_id_header}
    response = await app_client.get("/health", headers=headers)
    assert "x-correlation-id" in response.headers
    assert response.headers["x-correlation-id"] == "test-correlation-id"


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(app_client: AsyncClient) -> None:
    """Request without X-API-Key returns 401."""
    response = await app_client.get("/api/v1/pet/1")
    assert response.status_code == 401
