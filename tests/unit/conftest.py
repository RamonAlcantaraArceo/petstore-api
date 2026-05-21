"""Unit test configuration — all repositories are mocked."""

import allure
import pytest


@pytest.fixture(autouse=True)
def add_allure_layer() -> None:
    """Add a default 'unit' layer label to all tests in this module."""
    allure.dynamic.label("layer", "unit")
