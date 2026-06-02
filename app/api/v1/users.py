"""User endpoints — /api/v1/user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Response
from petstore_core.config import Settings
from petstore_core.schemas.user import User, UserCreate, UserLogin, UserUpdate
from petstore_core.services.user import UserService

from app.api.v1.error_mapping import map_domain_errors
from app.auth.dev_jwt import issue_dev_jwt
from app.models.user import UserModel
from app.dependencies import _cached_settings, _cached_settings, get_user_service

protected_router = APIRouter(prefix="/user", tags=["user"])
unprotected_router = APIRouter(prefix="/user", tags=["user"])


@unprotected_router.post("", response_model=User, status_code=200, operation_id="create_user")
async def create_user(
    user: Annotated[
        UserCreate,
        Body(
            description="User data for the new user to be created",
            openapi_examples={
                "example1": {
                    "summary": "Create user example",
                    "value": {
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "johndoe@example.com",
                        "phone": "555-1234",
                        "password": "securepassword",
                        "user_status": 1,
                    },
                },
                "example2": {
                    "summary": "Minimal data example",
                    "value": {"username": "janedoe", "password": "securepassword"},
                },
                "example3": {
                    "summary": "Invalid user example",
                    "value": {
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "johndoe@example.com",
                        "phone": "555-1234",
                        "user_status": 1,
                    },
                },
            },
        ),
    ],
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Create a new user.

    \f

    Args:
        user: User data from request body.
        service: Injected UserService.

    Returns:
        The created user.
    """
    return await map_domain_errors(service.create_user(user))


@unprotected_router.post(
    "/createWithList",
    response_model=list[User],
    status_code=200,
    operation_id="create_users_with_list",
)
async def create_users_with_list(
    users: list[UserCreate],
    service: Annotated[UserService, Depends(get_user_service)],
) -> list[User]:
    """Create users from a list.
    \f
    Args:
        users: List of user data from request body.
        service: Injected UserService.

    Returns:
        List of created users.
    """
    return await map_domain_errors(service.create_users_with_list(users))


@unprotected_router.get("/login", operation_id="login_user", response_model=UserLogin)
async def login_user(
    username: Annotated[str, Query(description="The username for login")],
    password: Annotated[str, Query(description="The password for login")],
    response: Response,
    service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> UserLogin:
    """Log user into the system.

    Args:
        username: The username to log in with.
        password: The password to log in with.
        service: Injected UserService.

    Returns:
        UserLogin containing the session token and user information.
    """
    await map_domain_errors(service.login(username, password))
    user = await map_domain_errors(service.get_user(username))
    user_model = UserModel(**user.model_dump())

    access_token = issue_dev_jwt(
        user=user_model,
        secret=settings.dev_jwt_secret,
        lifetime_seconds=settings.dev_jwt_expiration_seconds,
    )

    response.headers["Authorization"] = f"Bearer {access_token}"

    return UserLogin(access_token=access_token, token_type="bearer")


@protected_router.get("/logout", status_code=200, operation_id="logout_user")
async def logout_user(
    service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, str]:
    """Log out current logged-in user session.

    Args:
        service: Injected UserService.

    Returns:
        Confirmation message.
    """
    await map_domain_errors(service.logout())
    return {"message": "User logged out"}


@protected_router.get("/{username}", response_model=User, operation_id="get_user_by_name")
async def get_user_by_name(
    username: str,
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Get user by username.

    Args:
        username: The user's username.
        service: Injected UserService.

    Returns:
        The user with the given username.
    """
    return await map_domain_errors(service.get_user(username))


@protected_router.put("/{username}", response_model=User, operation_id="update_user")
async def update_user(
    username: str,
    user: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Update user by username.

    Args:
        username: The user's current username.
        user: Updated user data.
        service: Injected UserService.

    Returns:
        The updated user.
    """
    return await map_domain_errors(service.update_user(username, user))


@protected_router.delete("/{username}", status_code=200, operation_id="delete_user")
async def delete_user(
    username: str,
    service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, str]:
    """Delete user by username.

    Args:
        username: The user's unique username.
        service: Injected UserService.

    Returns:
        Confirmation message.
    """
    await map_domain_errors(service.delete_user(username))
    return {"message": "User deleted"}
