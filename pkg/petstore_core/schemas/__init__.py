"""Schemas package."""

from petstore_core.schemas.auth import (
    DevLoginRequest,
    DevLoginResponse,
    LoginRequest,
    LoginResponse,
    LoginUser,
)
from petstore_core.schemas.health import HealthDetails, HealthResponse
from petstore_core.schemas.order import Order, OrderCreate, OrderStatus
from petstore_core.schemas.pet import Category, Pet, PetCreate, PetStatus, PetUpdate, Tag
from petstore_core.schemas.user import User, UserCreate, UserUpdate

__all__ = [
    "HealthDetails",
    "HealthResponse",
    "Category",
    "Pet",
    "PetCreate",
    "PetStatus",
    "PetUpdate",
    "Tag",
    "Order",
    "OrderCreate",
    "OrderStatus",
    "User",
    "UserCreate",
    "UserUpdate",
    "DevLoginRequest",
    "DevLoginResponse",
    "LoginRequest",
    "LoginResponse",
    "LoginUser",
]
