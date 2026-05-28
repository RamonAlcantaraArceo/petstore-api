"""Compatibility wrapper for user schemas from petstore_core."""

from petstore_core.schemas.user import User, UserBase, UserCreate, UserUpdate

__all__ = ["UserBase", "UserCreate", "UserUpdate", "User"]
