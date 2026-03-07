"""Factory classes for generating test User data."""

from __future__ import annotations

import factory
from faker import Faker

from app.schemas.user import UserCreate

fake = Faker()


class UserCreateFactory(factory.Factory):
    """Factory for generating UserCreate instances.

    Example:
        >>> user = UserCreateFactory()
        >>> assert user.username
    """

    class Meta:
        """Factory metadata."""

        model = UserCreate

    username = factory.LazyFunction(lambda: fake.user_name() + "_" + fake.bothify("??###"))
    first_name = factory.LazyFunction(lambda: fake.first_name())
    last_name = factory.LazyFunction(lambda: fake.last_name())
    email = factory.LazyFunction(lambda: fake.email())
    phone = factory.LazyFunction(lambda: fake.phone_number()[:20])
    password = "testpassword123"
    user_status = 1
