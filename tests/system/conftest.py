"""System test configuration."""

import os

import allure
import pytest


@pytest.fixture(autouse=True)
def add_allure_layer() -> None:
    """Add a default 'system' layer label to all tests in this module."""
    allure.dynamic.label("layer", "system")

os.environ.setdefault("STORAGE_MODE", "memory")
os.environ.setdefault("API_KEY", "test-api-key")
