"""SQLAlchemy ORM model for Pet."""

from __future__ import annotations

from sqlalchemy import JSON, Column, Enum, Integer, String
from sqlalchemy.orm import DeclarativeBase


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

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status: Column[str] = Column(
        Enum("available", "pending", "sold", name="pet_status"),
        default="available",
        nullable=False,
    )
    photo_urls = Column(JSON, default=list)
    category = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
