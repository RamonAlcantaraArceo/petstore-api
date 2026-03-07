"""Integration tests for User API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.factories.user import UserCreateFactory


@pytest.mark.asyncio
async def test_create_user(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """POST /api/v1/user creates a user."""
    user_data = UserCreateFactory()
    payload = {
        "username": user_data.username,
        "firstName": user_data.first_name,
        "lastName": user_data.last_name,
        "email": user_data.email,
    }
    response = await app_client.post("/api/v1/user", json=payload, headers=api_key_header)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user_data.username


@pytest.mark.asyncio
async def test_get_user_by_username(
    app_client: AsyncClient, api_key_header: dict[str, str]
) -> None:
    """GET /api/v1/user/{username} returns the user."""
    user_data = UserCreateFactory()
    await app_client.post(
        "/api/v1/user",
        json={"username": user_data.username},
        headers=api_key_header,
    )
    response = await app_client.get(f"/api/v1/user/{user_data.username}", headers=api_key_header)
    assert response.status_code == 200
    assert response.json()["username"] == user_data.username


@pytest.mark.asyncio
async def test_get_user_not_found(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/user/{username} returns 404 when not found."""
    response = await app_client.get("/api/v1/user/nonexistent_user", headers=api_key_header)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """PUT /api/v1/user/{username} updates the user."""
    user_data = UserCreateFactory()
    await app_client.post(
        "/api/v1/user",
        json={"username": user_data.username},
        headers=api_key_header,
    )
    update_resp = await app_client.put(
        f"/api/v1/user/{user_data.username}",
        json={"first_name": "NewName"},
        headers=api_key_header,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["first_name"] == "NewName"


@pytest.mark.asyncio
async def test_delete_user(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """DELETE /api/v1/user/{username} removes the user."""
    user_data = UserCreateFactory()
    await app_client.post(
        "/api/v1/user",
        json={"username": user_data.username},
        headers=api_key_header,
    )
    del_resp = await app_client.delete(f"/api/v1/user/{user_data.username}", headers=api_key_header)
    assert del_resp.status_code == 200

    get_resp = await app_client.get(f"/api/v1/user/{user_data.username}", headers=api_key_header)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_user_login(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/user/login returns a token."""
    user_data = UserCreateFactory()
    await app_client.post(
        "/api/v1/user",
        json={"username": user_data.username},
        headers=api_key_header,
    )
    response = await app_client.get(
        f"/api/v1/user/login?username={user_data.username}&password=testpass",
        headers=api_key_header,
    )
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.asyncio
async def test_user_logout(app_client: AsyncClient, api_key_header: dict[str, str]) -> None:
    """GET /api/v1/user/logout returns 200."""
    response = await app_client.get("/api/v1/user/logout", headers=api_key_header)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_users_with_list(
    app_client: AsyncClient, api_key_header: dict[str, str]
) -> None:
    """POST /api/v1/user/createWithList creates multiple users."""
    users = [{"username": f"bulk_user_{i}", "email": f"user{i}@example.com"} for i in range(3)]
    response = await app_client.post(
        "/api/v1/user/createWithList", json=users, headers=api_key_header
    )
    assert response.status_code == 200
    assert len(response.json()) == 3
