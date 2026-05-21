"""Integration test configuration."""

import os

import allure
import pytest


@pytest.fixture(autouse=True)
def add_allure_layer() -> None:
    """Add a default 'integration' layer label to all tests in this module."""
    allure.dynamic.label("layer", "integration")


os.environ.setdefault("STORAGE_MODE", "memory")
os.environ.setdefault("API_KEY", "test-api-key")
