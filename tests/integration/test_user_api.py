"""Integration tests for User API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

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
        "password": user_data.password,
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
    created_response = await app_client.post(
        "/api/v1/user",
        json=user_data.model_dump(),
        headers=api_key_header,
    )
    assert created_response.status_code == 200
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
    created_user = await app_client.post(
        "/api/v1/user",
        json=user_data.model_dump(),
        headers=api_key_header,
    )
    assert created_user.status_code == 200
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
    created_user = await app_client.post(
        "/api/v1/user",
        json=user_data.model_dump(),
        headers=api_key_header,
    )
    assert created_user.status_code == 200
    del_resp = await app_client.delete(f"/api/v1/user/{user_data.username}", headers=api_key_header)
    assert del_resp.status_code == 204

    get_resp = await app_client.get(f"/api/v1/user/{user_data.username}", headers=api_key_header)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_post_user_login_is_canonical(
    app_client: AsyncClient, api_key_header: dict[str, str]
) -> None:
    """POST /api/v1/user/login accepts JSON credentials and returns user details."""
    user_data = UserCreateFactory()
    credentials = {"email": user_data.email, "password": user_data.password}
    created_user = await app_client.post(
        "/api/v1/user",
        json=user_data.model_dump(),
        headers=api_key_header,
    )
    assert created_user.status_code == 200
    response = await app_client.post(
        "/api/v1/user/login",
        json=credentials,
        headers=api_key_header,
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["email"] == user_data.email


@pytest.mark.asyncio
async def test_post_user_login_rejects_invalid_credentials(
    app_client: AsyncClient, api_key_header: dict[str, str]
) -> None:
    """POST /api/v1/user/login returns a clear authentication error."""
    response = await app_client.post(
        "/api/v1/user/login",
        json={"email": "missing@example.com", "password": "wrong"},
        headers=api_key_header,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials."


@pytest.mark.asyncio
async def test_legacy_get_login_matches_post_response_shape(
    app_client: AsyncClient,
    api_key_header: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deprecated GET /api/v1/user/login retains the POST response contract."""
    warning = MagicMock()
    monkeypatch.setattr("app.api.v1.users.log.warning", warning)
    user_data = UserCreateFactory()
    created_user = await app_client.post(
        "/api/v1/user",
        json=user_data.model_dump(),
        headers=api_key_header,
    )
    assert created_user.status_code == 200

    post_response = await app_client.post(
        "/api/v1/user/login",
        json={"email": user_data.email, "password": user_data.password},
        headers=api_key_header,
    )
    get_response = await app_client.get(
        "/api/v1/user/login",
        params={"username": user_data.email, "password": user_data.password},
        headers=api_key_header,
    )

    assert post_response.status_code == get_response.status_code == 200
    assert post_response.json().keys() == get_response.json().keys()
    assert post_response.json()["user"].keys() == get_response.json()["user"].keys()
    warning.assert_called_once_with(
        "deprecated_login_endpoint_used",
        method="GET",
        path="/user/login",
        replacement="POST /user/login",
    )


@pytest.mark.asyncio
async def test_dev_login_auth_endpoint_accepts_user_created_via_user_api(
    app_client: AsyncClient, api_key_header: dict[str, str]
) -> None:
    """POST /api/v1/user/auth can issue tokens for newly created in-memory users."""
    user_data = UserCreateFactory()
    created_user = await app_client.post(
        "/api/v1/user",
        json=user_data.model_dump(),
        headers=api_key_header,
    )
    assert created_user.status_code == 200

    response = await app_client.post(
        "/api/v1/user/auth",
        json={"username": user_data.username},
        headers=api_key_header,
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == user_data.username


@pytest.mark.asyncio
async def test_login_openapi_prefers_post_and_deprecates_get(app_client: AsyncClient) -> None:
    """OpenAPI marks only the Petstore-compatible GET login as deprecated."""
    schema = (await app_client.get("/openapi.json")).json()
    login_operations = schema["paths"]["/api/v1/user/login"]

    assert login_operations["post"].get("deprecated") is not True
    assert login_operations["get"]["deprecated"] is True


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
    users = [
        {"username": f"bulk_user_{i}", "email": f"user{i}@example.com", "password": "testpass"}
        for i in range(3)
    ]
    response = await app_client.post(
        "/api/v1/user/createWithList", json=users, headers=api_key_header
    )
    assert response.status_code == 200
    assert len(response.json()) == 3
