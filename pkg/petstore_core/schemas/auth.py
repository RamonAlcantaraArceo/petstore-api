"""Pydantic schemas for Auth resources."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .user import User


class DevLoginRequest(BaseModel):
    """Request payload for development login."""

    username: str = Field(description="Seeded development username.")

    model_config = {"json_schema_extra": {"example": {"username": "devuser"}}}


class DevLoginResponse(BaseModel):
    """Response payload for development login."""

    access_token: str = Field(description="JWT access token for authenticated user.")
    token_type: str = Field(description="Type of the token, typically 'bearer'.")
    user: User = Field(description="Authenticated user details.")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "access_token": ("dev-header.dev-payload.dev-signature"),
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
        },
    }
