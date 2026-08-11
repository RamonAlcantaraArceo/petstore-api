"""User endpoints — /api/v1/user."""

from __future__ import annotations

import contextlib
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from petstore_core.config import Settings
from petstore_core.errors import NotFoundError
from petstore_core.models.user import UserModel
from petstore_core.schemas.user import User, UserCreate, UserLogin, UserUpdate
from petstore_core.services.user import UserService

from app.api.deps import bearer_scheme, get_current_user
from app.api.v1.error_mapping import map_domain_errors
from app.auth.dev_jwt import issue_dev_jwt
from app.auth.supabase_auth import (
    SupabaseAuthNotConfiguredError,
    supabase_delete_user,
    supabase_get_user_by_email,
    supabase_sign_in,
    supabase_sign_out,
    supabase_sign_up,
    supabase_update_user,
)
from app.dependencies import _cached_settings, get_user_service

log = structlog.get_logger(__name__)

protected_router = APIRouter(prefix="/user", tags=["user"])
unprotected_router = APIRouter(prefix="/user", tags=["user"])

_IS_SUPABASE_ENV = {"staging", "prod"}


def _user_model_to_schema(user: UserModel) -> User:
    """Convert a UserModel to a User schema."""
    return User(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        user_status=user.user_status,
    )


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
            },
        ),
    ],
    service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> User:
    """Create a new user.

    In staging/prod this proxies through Supabase Auth — the user account is
    created in Supabase first, then a local profile row is mirrored. The caller
    sees the same response schema in all environments.
    \f
    Args:
        user: User data from request body.
        service: Injected UserService.
        settings: Application settings.

    Returns:
        The created user.
    """
    if settings.app_env in _IS_SUPABASE_ENV:
        if not user.email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="email is required when creating users in staging/prod.",
            )
        try:
            supabase_user = await supabase_sign_up(
                user.email,
                user.password,
                metadata={
                    k: v
                    for k, v in {
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "phone": user.phone,
                        "user_status": user.user_status,
                    }.items()
                    if v is not None
                },
                settings=settings,
            )
        except SupabaseAuthNotConfiguredError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase Auth is not configured.",
            ) from exc

        supabase_uuid = supabase_user.get("id", "")
        effective_username = user.username or user.email
        local_user = UserCreate(
            username=effective_username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone=user.phone,
            password=user.password,
            user_status=user.user_status,
        )
        created = await map_domain_errors(service.create_user(local_user))
        log.info(
            "user.created_via_supabase", supabase_id=supabase_uuid, username=effective_username
        )
        return created

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
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> list[User]:
    """Create users from a list.

    In staging/prod each user is proxied through Supabase Auth individually.
    \f
    Args:
        users: List of user data from request body.
        service: Injected UserService.
        settings: Application settings.

    Returns:
        List of created users.
    """
    if settings.app_env in _IS_SUPABASE_ENV:
        created_users: list[User] = []
        for user in users:
            if not user.email:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"email is required for all users in staging/prod (missing for username={user.username!r}).",
                )
            try:
                await supabase_sign_up(
                    user.email,
                    user.password,
                    metadata={
                        k: v
                        for k, v in {
                            "username": user.username,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "phone": user.phone,
                            "user_status": user.user_status,
                        }.items()
                        if v is not None
                    },
                    settings=settings,
                )
            except SupabaseAuthNotConfiguredError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Supabase Auth is not configured.",
                ) from exc
            effective_username = user.username or user.email
            local_user = UserCreate(
                username=effective_username,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone=user.phone,
                password=user.password,
                user_status=user.user_status,
            )
            created = await map_domain_errors(service.create_user(local_user))
            created_users.append(created)
        return created_users

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
    \f
    Args:
        username: The username to log in with (email for Supabase environments).
        password: The password to log in with.
        service: Injected UserService.
        settings: Application settings.

    Returns:
        UserLogin containing the session token and user information.
    """
    if settings.app_env in _IS_SUPABASE_ENV:
        try:
            token_data = await supabase_sign_in(username, password, settings=settings)
        except SupabaseAuthNotConfiguredError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Supabase Auth is not configured. Set SUPABASE_URL and "
                    "SUPABASE_PUBLISHABLE_KEY (or SUPABASE_ANON_KEY)."
                ),
            ) from exc
        access_token: str = token_data["access_token"]
        response.headers["Authorization"] = f"Bearer {access_token}"
        return UserLogin(access_token=access_token, token_type="bearer")

    await map_domain_errors(service.login(username, password))
    user = await map_domain_errors(service.get_user(username))
    user_model = UserModel(**user.model_dump())

    dev_token = issue_dev_jwt(
        user=user_model,
        secret=settings.dev_jwt_secret,
        lifetime_seconds=settings.dev_jwt_expiration_seconds,
    )

    response.headers["Authorization"] = f"Bearer {dev_token}"

    return UserLogin(access_token=dev_token, token_type="bearer")


@protected_router.get("/logout", status_code=200, operation_id="logout_user")
async def logout_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> dict[str, str]:
    """Log out current logged-in user session.
    \f
    Args:
        credentials: Bearer token from the Authorization header.
        service: Injected UserService.
        settings: Application settings.

    Returns:
        Confirmation message.
    """
    if settings.app_env in _IS_SUPABASE_ENV and credentials is not None:
        with contextlib.suppress(SupabaseAuthNotConfiguredError):
            await supabase_sign_out(credentials.credentials, settings=settings)

    await map_domain_errors(service.logout())
    return {"message": "User logged out"}


@protected_router.get("/me", response_model=User, operation_id="get_current_user_profile")
async def get_current_user_profile(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> User:
    """Return the profile of the currently authenticated user.

    Resolves the user from JWT claims in all environments. This is the
    recommended endpoint for getting "my own profile" in staging/prod since
    Supabase users do not have a username that can be used with
    ``GET /user/{username}``.
    \f
    Args:
        current_user: Injected authenticated user.

    Returns:
        The authenticated user\'s profile.
    """
    return _user_model_to_schema(current_user)


@protected_router.get("/{username}", response_model=User, operation_id="get_user_by_name")
async def get_user_by_name(
    username: str,
    service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> User:
    """Get user by username.

    In staging/prod this endpoint is not supported because Supabase users do
    not have a username concept. Use ``GET /user/me`` instead.
    \f
    Args:
        username: The user\'s username.
        service: Injected UserService.
        settings: Application settings.

    Returns:
        The user with the given username.
    """
    if settings.app_env in _IS_SUPABASE_ENV:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Username-based lookup is not supported in this environment. "
                "Use GET /user/me to retrieve your own profile."
            ),
        )
    return await map_domain_errors(service.get_user(username))


@protected_router.put("/{username}", response_model=User, operation_id="update_user")
async def update_user(
    username: str,
    user: UserUpdate,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> User:
    """Update user by username.

    In staging/prod, email and phone changes are synced to Supabase Auth
    before the local DB is updated. Username changes are rejected.
    \f
    Args:
        username: The user\'s current username (used for local DB lookup in dev).
        user: Updated user data.
        credentials: Bearer token from the Authorization header.
        service: Injected UserService.
        settings: Application settings.

    Returns:
        The updated user.
    """
    if settings.app_env in _IS_SUPABASE_ENV:
        if user.username is not None and user.username != username:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username changes are not supported in staging/prod.",
            )
        if credentials is not None:
            metadata: dict[str, Any] = {}
            if user.first_name is not None:
                metadata["first_name"] = user.first_name
            if user.last_name is not None:
                metadata["last_name"] = user.last_name
            if user.phone is not None:
                metadata["phone"] = user.phone
            if user.user_status is not None:
                metadata["user_status"] = user.user_status
            with contextlib.suppress(SupabaseAuthNotConfiguredError, HTTPException):
                await supabase_update_user(
                    credentials.credentials,
                    email=user.email,
                    phone=user.phone,
                    metadata=metadata or None,
                    settings=settings,
                )

    return await map_domain_errors(service.update_user(username, user))


@unprotected_router.delete("/{username}", status_code=204, operation_id="delete_user")
async def delete_user(
    username: str,
    service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> None:
    """Delete user by username.

    In staging/prod the user\'s Supabase Auth account is permanently deleted
    first, then the local DB profile is removed.
    Requires a server-side Supabase admin key (`SUPABASE_SECRET_API_KEY`
    preferred; `SUPABASE_SERVICE_ROLE_KEY` still supported) — returns 501 if
    the key is not set.
    \f
    Args:
        username: The user\'s unique username.
        service: Injected UserService.
        settings: Application settings.

    Returns:
        None (204 No Content).
    """
    if settings.app_env in _IS_SUPABASE_ENV:
        if not settings.supabase_service_role_key:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    "User deletion requires SUPABASE_SECRET_API_KEY "
                    "(or SUPABASE_SERVICE_ROLE_KEY) to be configured. "
                    "Set it in your environment to enable this operation."
                ),
            )
        target_email = username
        if "@" not in target_email:
            user_profile = await map_domain_errors(service.get_user(username))
            if not user_profile.email:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cannot delete Supabase user without an email on the profile.",
                )
            target_email = user_profile.email

        metadata_username: str | None = None
        try:
            supabase_user = await supabase_get_user_by_email(target_email, settings=settings)
            supabase_user_uuid = supabase_user["id"]
            await supabase_delete_user(supabase_user_uuid, settings=settings)
            log.info("user.deleted_in_supabase", username=username, email=target_email)

            raw_metadata = supabase_user.get("user_metadata")
            metadata_username = (
                raw_metadata.get("username") if isinstance(raw_metadata, dict) else None
            )
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise
            # If the Supabase account is already gone, still clean the local mirror.
            log.info("user.already_deleted_in_supabase", username=username, email=target_email)

        delete_candidates = [
            username,
            target_email,
            metadata_username if isinstance(metadata_username, str) else None,
        ]
        seen: set[str] = set()
        deleted_local = False
        for candidate in delete_candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                await service.delete_user(candidate)
                deleted_local = True
                break
            except NotFoundError:
                continue

        if not deleted_local:
            log.warning(
                "user.profile_not_found_after_supabase_delete",
                username=username,
                email=target_email,
                metadata_username=metadata_username,
            )
        return

    await map_domain_errors(service.delete_user(username))
    return
