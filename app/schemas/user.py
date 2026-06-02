"""Compatibility wrapper for user schemas from petstore_core."""

from petstore_core.schemas.user import User, UserBase, UserCreate, UserLogin, UserUpdate

__all__ = ["UserBase", "UserCreate", "UserUpdate", "UserLogin", "User"]
