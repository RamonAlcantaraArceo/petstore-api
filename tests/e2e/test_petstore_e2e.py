"""End-to-end tests against a live staging environment."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.remote_only
@pytest.mark.backend_agnostic
async def test_e2e_health(remote_client: AsyncClient) -> None:
    """Smoke test: GET /health returns 200.

    Args:
        remote_client: Client pointing at the live service.
    """
    response = await remote_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
@pytest.mark.remote_only
@pytest.mark.backend_agnostic
async def test_e2e_pet_crud(
    remote_client: AsyncClient, remote_api_key_header: dict[str, str]
) -> None:
    """Smoke test: create and retrieve a pet.

    Args:
        remote_client: Client pointing at the live service.
    """
    create_resp = await remote_client.post(
        "/api/v1/pet",
        json={"name": "E2E Pet", "photoUrls": [], "status": "available"},
        headers=remote_api_key_header,
    )
    assert create_resp.status_code == 200
    pet_id = create_resp.json()["id"]

    get_resp = await remote_client.get(f"/api/v1/pet/{pet_id}", headers=remote_api_key_header)
    assert get_resp.status_code == 200
