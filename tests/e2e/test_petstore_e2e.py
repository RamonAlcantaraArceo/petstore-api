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
