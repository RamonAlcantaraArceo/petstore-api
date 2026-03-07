"""Factory classes for generating test Pet data."""

from __future__ import annotations

import factory
from faker import Faker

from app.schemas.pet import PetCreate, PetStatus

fake = Faker()


class PetCreateFactory(factory.Factory):
    """Factory for generating PetCreate instances.

    Example:
        >>> pet = PetCreateFactory()
        >>> assert pet.name
    """

    class Meta:
        """Factory metadata."""

        model = PetCreate

    name = factory.LazyFunction(lambda: fake.first_name())
    photo_urls = factory.LazyFunction(lambda: [fake.image_url()])
    status = PetStatus.available
