"""Schemas package."""

from app.schemas.auth import DevLoginRequest, DevLoginResponse
from app.schemas.health import HealthDetails, HealthResponse
from app.schemas.order import Order, OrderCreate, OrderStatus
from app.schemas.pet import Category, Pet, PetCreate, PetStatus, PetUpdate, Tag
from app.schemas.user import User, UserCreate, UserLogin, UserUpdate

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
    "UserLogin",
    "DevLoginRequest",
    "DevLoginResponse",
]
