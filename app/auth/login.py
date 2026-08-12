"""Shared user login service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, status
from petstore_core.config import Settings
from petstore_core.errors import ValidationError
from petstore_core.models.user import UserModel
from petstore_core.schemas.auth import LoginResponse, LoginUser
from petstore_core.services.user import UserService

from app.api.v1.error_mapping import map_domain_errors
from app.auth.dev_jwt import issue_dev_jwt
from app.auth.dev_store import authenticate_dev_user
from app.auth.supabase_auth import SupabaseAuthNotConfiguredError, supabase_sign_in
from app.auth.supabase_jwt import validate_supabase_jwt

_IS_SUPABASE_ENV = {"staging", "prod"}


async def perform_login(
    email: str,
    password: str,
    *,
    service: UserService,
    settings: Settings,
) -> LoginResponse:
    """Authenticate credentials and return a unified login response.

    Args:
        email: Supabase email or development-compatible username.
        password: User password.
        service: User service used by development storage.
        settings: Application settings.

    Returns:
        Access token and authenticated user identity.
    """
    if settings.app_env in _IS_SUPABASE_ENV:
        try:
            token_data = await supabase_sign_in(email, password, settings=settings)
        except SupabaseAuthNotConfiguredError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Supabase Auth is not configured. Set SUPABASE_URL and "
                    "SUPABASE_PUBLISHABLE_KEY (or SUPABASE_ANON_KEY)."
                ),
            ) from exc
        access_token = _required_string(token_data, "access_token")
        claims = await validate_supabase_jwt(access_token, settings=settings)
        metadata = claims.get("user_metadata")
        user_metadata = metadata if isinstance(metadata, Mapping) else {}
        return LoginResponse(
            access_token=access_token,
            token_type=_optional_string(token_data.get("token_type")) or "bearer",
            user=LoginUser(
                id=_required_string(claims, "sub"),
                email=_optional_string(claims.get("email")),
                username=_optional_string(user_metadata.get("username")),
            ),
        )

    if settings.app_env == "dev" and settings.dev_in_memory_auth_enabled:
        user_model = authenticate_dev_user(email, password)
        if user_model is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = user_model
    else:
        try:
            await service.login(email, password)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        resolved = await map_domain_errors(service.get_user(email))
        user_model = _to_user_model(resolved)
        user = user_model

    return LoginResponse(
        access_token=issue_dev_jwt(
            user=user_model,
            secret=settings.dev_jwt_secret,
            lifetime_seconds=settings.dev_jwt_expiration_seconds,
        ),
        token_type="bearer",
        user=LoginUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
        ),
    )


def _required_string(values: Mapping[str, Any], key: str) -> str:
    """Return a required non-empty string from a response mapping."""
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Authentication response is missing {key!r}.")
    return value


def _optional_string(value: Any) -> str | None:
    """Return a string value when present."""
    return value if isinstance(value, str) else None


def _to_user_model(user: Any) -> UserModel:
    """Convert supported user payloads to ``UserModel``."""
    if isinstance(user, UserModel):
        return user
    return UserModel(**user.model_dump())
