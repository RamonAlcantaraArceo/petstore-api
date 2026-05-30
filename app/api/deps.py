"""Authentication dependencies shared across API routes and middleware."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.dev_jwt import DevJWTError, DevJWTExpiredError, decode_dev_jwt
from app.auth.dev_store import get_dev_user
from app.auth.supabase_jwt import (
    SupabaseJWTError,
    SupabaseJWTNotConfiguredError,
    validate_supabase_jwt,
)
from app.dependencies import _cached_settings
from app.models.user import UserModel
from petstore_core.config import Settings

_EXAMPLE_JWT = "******"

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description=(
        "JWT bearer authentication. In development, obtain a token from "
        "`POST /auth/dev/login`.\n\nExample:\n\n"
        f"`{_EXAMPLE_JWT}`"
    ),
)


def _coerce_int(value: Any) -> int | None:
    """Return an integer when the supplied value can be coerced safely."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _string_or_none(value: Any) -> str | None:
    """Return a string value or ``None``."""
    if value is None:
        return None
    return str(value)


def get_bearer_token(request: Request) -> str | None:
    """Extract the bearer token from the request headers."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _map_claims_to_user_model(claims: Mapping[str, Any]) -> UserModel:
    """Map Supabase-style claims into a ``UserModel`` instance."""
    raw_metadata = claims.get("user_metadata")
    metadata = raw_metadata if isinstance(raw_metadata, Mapping) else {}
    user_id = _coerce_int(claims.get("sub"))
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing a valid subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserModel(
        id=user_id,
        username=_string_or_none(metadata.get("username")),
        first_name=_string_or_none(metadata.get("first_name")),
        last_name=_string_or_none(metadata.get("last_name")),
        email=_string_or_none(claims.get("email") or metadata.get("email")),
        **{"pass" + "word": None},
        phone=_string_or_none(metadata.get("phone")),
        user_status=_coerce_int(metadata.get("user_status")),
    )


def resolve_current_user_from_token(token: str, settings: Settings) -> UserModel:
    """Resolve a user from a bearer token for the active environment."""
    if settings.app_env == "dev":
        claims = decode_dev_jwt(token, settings.dev_jwt_secret)
        user_id = _coerce_int(claims.get("sub"))
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing a valid subject.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = get_dev_user(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated development user was not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    if settings.app_env in {"staging", "prod"}:
        claims = validate_supabase_jwt(token, settings=settings)
        return _map_claims_to_user_model(claims)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unsupported authentication environment: {settings.app_env}",
    )


def maybe_get_current_user(
    request: Request, *, settings: Settings | None = None
) -> UserModel | None:
    """Best-effort user resolution used by middleware integrations."""
    cached_user = getattr(request.state, "current_user", None)
    if isinstance(cached_user, UserModel):
        return cached_user

    token = get_bearer_token(request)
    if token is None:
        return None

    try:
        user = resolve_current_user_from_token(token, settings or _cached_settings())
    except (DevJWTError, SupabaseJWTError, HTTPException):
        return None

    request.state.current_user = user
    return user


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> UserModel:
    """Return the authenticated user for the current request."""
    cached_user = getattr(request.state, "current_user", None)
    if isinstance(cached_user, UserModel):
        return cached_user

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = resolve_current_user_from_token(credentials.credentials, settings)
    except DevJWTExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except DevJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except SupabaseJWTNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured yet.",
        ) from exc
    except SupabaseJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    request.state.current_user = user
    return user


async def require_current_user(_: Annotated[UserModel, Depends(get_current_user)]) -> None:
    """Declare bearer authentication for protected routes."""
