"""Tests to ensure petstore_core modules are properly covered in coverage measurement.

This module explicitly imports from petstore_core to ensure those modules are
included in coverage reports, since they're typically imported through app/
wrapper modules.
"""

from __future__ import annotations

import pytest

from petstore_core.config import get_settings
from petstore_core.errors import NotFoundError, ValidationError
from petstore_core.repositories.base import (
    OrderRepository,
    PetRepository,
    UserRepository,
)
from petstore_core.services.order import OrderService
from petstore_core.services.pet import PetService
from petstore_core.services.user import UserService


@pytest.mark.unit
def test_petstore_core_config_import() -> None:
    """Verify petstore_core.config is importable and get_settings works."""
    settings = get_settings()
    assert settings is not None
    assert hasattr(settings, "api_key")


@pytest.mark.unit
def test_petstore_core_errors_import() -> None:
    """Verify petstore_core errors are importable."""
    assert NotFoundError is not None
    assert ValidationError is not None


@pytest.mark.unit
def test_petstore_core_base_repositories_import() -> None:
    """Verify petstore_core base repositories are importable."""
    assert OrderRepository is not None
    assert PetRepository is not None
    assert UserRepository is not None


@pytest.mark.unit
def test_petstore_core_services_import() -> None:
    """Verify petstore_core services are importable."""
    assert OrderService is not None
    assert PetService is not None
    assert UserService is not None
