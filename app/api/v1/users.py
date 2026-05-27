"""User endpoints — /api/v1/user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.error_mapping import map_domain_errors
from app.dependencies import get_user_service
from petstore_core.schemas.user import User, UserCreate, UserUpdate
from petstore_core.services.user import UserService

router = APIRouter(prefix="/user", tags=["user"])


@router.post("", response_model=User, status_code=200, operation_id="create_user")
async def create_user(
    user: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Create a new user.

    Args:
        user: User data from request body.
        service: Injected UserService.

    Returns:
        The created user.
    """
    return await map_domain_errors(service.create_user(user))


@router.post(
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

    Args:
        users: List of user data from request body.
        service: Injected UserService.

    Returns:
        List of created users.
    """
    return await map_domain_errors(service.create_users_with_list(users))


@router.get("/login", operation_id="login_user")
async def login_user(
    username: Annotated[str, Query(description="The username for login")],
    password: Annotated[str, Query(description="The password for login")],
    service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, str]:
    """Log user into the system.

    Args:
        username: The username to log in with.
        password: The password to log in with.
        service: Injected UserService.

    Returns:
        Dict containing the session token.
    """
    token = await map_domain_errors(service.login(username, password))
    return {"token": token}


@router.get("/logout", status_code=200, operation_id="logout_user")
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


@router.get("/{username}", response_model=User, operation_id="get_user_by_name")
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


@router.put("/{username}", response_model=User, operation_id="update_user")
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


@router.delete("/{username}", status_code=200, operation_id="delete_user")
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
