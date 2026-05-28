"""Pydantic schemas for User resources."""

from __future__ import annotations

from pydantic import BaseModel


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

    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    user_status: int | None = None

    model_config = {"populate_by_name": True}


class UserCreate(UserBase):
    """Schema for creating a new user.

    Attributes:
        password: User's plain-text password (hashed before storage).
    """

    password: str | None = None


class UserUpdate(UserBase):
    """Schema for updating an existing user.

    Attributes:
        password: New password (optional).
    """

    password: str | None = None


class User(UserBase):
    """Full user schema including server-assigned fields.

    Attributes:
        id: User identifier.
    """

    id: int | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}
