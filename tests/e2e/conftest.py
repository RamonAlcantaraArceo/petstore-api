"""E2E test configuration — targets a live service URL."""

import os

import pytest

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip all e2e tests when E2E_BASE_URL is not configured.

    Args:
        items: Collected test items.
    """
    if not E2E_BASE_URL:
        skip_marker = pytest.mark.skip(reason="E2E_BASE_URL not set — skipping e2e tests")
        for item in items:
            if "e2e" in str(item.fspath):
                item.add_marker(skip_marker)
