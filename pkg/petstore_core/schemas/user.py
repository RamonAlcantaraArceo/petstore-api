"""Pydantic schemas for User resources."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    """Schema for user login response.

    Attributes:
        access_token: JWT token issued upon successful login.
        token_type: Type of the issued token (e.g., "bearer").
    """

    access_token: str = Field(description="JWT token issued upon successful login.")
    token_type: str = Field(description="Type of the issued token (e.g., 'bearer').")


class UserBase(BaseModel):
    """Base user schema with shared fields.

    Attributes:
        username: Unique username.
        first_name: User's first name.
        last_name: User's last name.
        email: User's email address.
        phone: User's phone number.
        user_status: User status code.
    """

    username: str = Field(description="Unique username.")
    first_name: str | None = Field(
        default=None, description="User's first name.", examples=["Patricia", "John"]
    )
    last_name: str | None = Field(default=None, description="User's last name.")
    email: str | None = Field(default=None, description="User's email address.")
    phone: str | None = Field(default=None, description="User's phone number.")
    user_status: int | None = Field(default=None, description="User status code.")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "username": "johndoe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "johndoe@example.com",
                    "phone": "555-1234",
                    "user_status": 1,
                },
                {
                    "username": "patriciasmith",
                    "first_name": "Patricia",
                    "last_name": "Smith",
                    "email": "patriciasmith@example.com",
                    "phone": "555-5678",
                    "user_status": 1,
                },
            ]
        },
    }


class UserCreate(UserBase):
    """Schema for creating a new user.

    Attributes:
        password: User's plain-text password (hashed before storage).
    """

    password: str = Field(description="User's plain-text password (hashed before storage).")


class UserUpdate(UserBase):
    """Schema for updating an existing user.

    Attributes:
        password: New password (optional).
    """

    password: str | None = Field(default=None, description="New password (optional).")


class User(UserBase):
    """Full user schema including server-assigned fields.

    Attributes:
        id: User identifier.
    """

    id: int = Field(description="User identifier.")

    model_config = {"from_attributes": True, "populate_by_name": True}
