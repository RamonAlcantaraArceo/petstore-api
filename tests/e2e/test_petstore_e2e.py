"""End-to-end tests against a live staging environment."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import AsyncClient

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "")
E2E_API_KEY = os.environ.get("API_KEY", "dev-api-key")


@pytest_asyncio.fixture
async def e2e_client() -> AsyncClient:
    """Return an HTTPX async client pointing at the live E2E service.

    Yields:
        AsyncClient connected to E2E_BASE_URL.
    """
    async with AsyncClient(base_url=E2E_BASE_URL, timeout=30) as client:
        yield client


@pytest.mark.asyncio
async def test_e2e_health(e2e_client: AsyncClient) -> None:
    """Smoke test: GET /health returns 200.

    Args:
        e2e_client: Client pointing at the live service.
    """
    response = await e2e_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_e2e_pet_crud(e2e_client: AsyncClient) -> None:
    """Smoke test: create and retrieve a pet.

    Args:
        e2e_client: Client pointing at the live service.
    """
    headers = {"X-API-Key": E2E_API_KEY}
    create_resp = await e2e_client.post(
        "/api/v1/pet",
        json={"name": "E2E Pet", "photoUrls": [], "status": "available"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    pet_id = create_resp.json()["id"]

    get_resp = await e2e_client.get(f"/api/v1/pet/{pet_id}", headers=headers)
    assert get_resp.status_code == 200
