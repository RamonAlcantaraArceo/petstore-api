"""SQLAlchemy ORM model for User."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_status: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)

