"""Development authentication routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dev_jwt import issue_dev_jwt
from app.auth.dev_store import get_dev_user_by_username
from app.dependencies import _cached_settings
from petstore_core.config import Settings
from petstore_core.schemas.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    """Request payload for development login."""

    username: str = Field(description="Seeded development username.", examples=["devuser"])


class DevLoginResponse(BaseModel):
    """Response payload for development login."""

    access_token: str
    token_type: str = "bearer"
    user: User

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": (
                    "dev-header."
                    "dev-payload."
                    "dev-signature"
                ),
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "username": "devuser",
                    "first_name": "Dev",
                    "last_name": "User",
                    "email": "dev@example.com",
                    "phone": "555-1234",
                    "user_status": 1,
                },
            }
        }
    }


@router.post(
    "/dev/login",
    response_model=DevLoginResponse,
    operation_id="dev_login",
    summary="DEV ONLY login",
    description=(
        "DEV ONLY. Exchange a seeded in-memory username for a Supabase-shaped "
        "development JWT."
    ),
    responses={
        401: {"description": "Unknown development username."},
        403: {"description": "Development login is disabled outside dev."},
    },
)
async def dev_login(
    payload: DevLoginRequest,
    settings: Annotated[Settings, Depends(_cached_settings)],
) -> DevLoginResponse:
    """Issue a development bearer token for a seeded user."""
    if settings.app_env != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development login is only available when APP_ENV/ENV is set to dev.",
        )

    user = get_dev_user_by_username(payload.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown development username.",
        )

    return DevLoginResponse(
        access_token=issue_dev_jwt(
            user,
            settings.dev_jwt_secret,
            lifetime_seconds=settings.dev_jwt_expiration_seconds,
        ),
        user=User.model_validate(user),
    )
