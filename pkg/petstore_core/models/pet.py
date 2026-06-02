"""SQLAlchemy ORM model for Pet."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Enum, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class PetModel(Base):
    """SQLAlchemy ORM model representing a pet.

    Attributes:
        id: Primary key.
        name: Pet name.
        status: Availability status.
        photo_urls: JSON list of photo URLs.
        category: JSON-encoded category dict.
        tags: JSON list of tag dicts.
    """

    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("available", "pending", "sold", name="pet_status"),
        default="available",
        nullable=False,
    )
    photo_urls: Mapped[list[Any]] = mapped_column(JSON, default=list)
    category: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

