"""SQLAlchemy ORM model for User."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class UserModel(Base):
    """SQLAlchemy ORM model representing a user.

    Attributes:
        id: Primary key.
        username: Unique username.
        first_name: User's first name.
        last_name: User's last name.
        email: User's email address.
        password: Hashed password.
        phone: User's phone number.
        user_status: User status code.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    user_status = Column(Integer, default=0, nullable=True)
