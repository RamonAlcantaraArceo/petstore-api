"""Shared test fixtures — app client, service factories, and entity factories."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import reset_memory_repos
from app.main import create_app


def _remote_base_url() -> str:
    """Return configured remote test URL, preferring TEST_BASE_URL over E2E_BASE_URL."""
    return os.environ.get("TEST_BASE_URL") or os.environ.get("E2E_BASE_URL", "")


def _remote_api_key() -> str:
    """Return API key used for remote/live tests."""
    return os.environ.get("API_KEY", "dev-api-key")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply intent markers and skip remote-only tests when URL is not configured."""
    remote_base_url = _remote_base_url()
    for item in items:
        path = str(item.fspath)
        e2e_norm_path = os.sep.join(["tests", "e2e"])
        integration_norm_path = os.sep.join(["tests", "integration"])
        system_norm_path = os.sep.join(["tests", "system"])
        if e2e_norm_path in os.path.normpath(path):
            item.add_marker(pytest.mark.remote_only)
        elif integration_norm_path in os.path.normpath(
            path
        ) or system_norm_path in os.path.normpath(path):
            item.add_marker(pytest.mark.memory_only)

    if not remote_base_url:
        skip_remote = pytest.mark.skip(
            reason="TEST_BASE_URL or E2E_BASE_URL not set — skipping remote_only tests"
        )
        for item in items:
            if "remote_only" in item.keywords:
                item.add_marker(skip_remote)


@pytest.fixture(autouse=True)
def reset_repos(request: pytest.FixtureRequest) -> None:
    """Reset all in-memory repositories before each test."""
    if "remote_only" in request.node.keywords:
        return
    reset_memory_repos()


@pytest_asyncio.fixture
async def memory_client() -> AsyncIterator[AsyncClient]:
    """Return an async HTTPX client targeting the in-memory FastAPI test app.

    Yields:
        AsyncClient connected to the test app.
    """
    os.environ.setdefault("STORAGE_MODE", "memory")
    os.environ.setdefault("API_KEY", "test-api-key")

    from app.dependencies import _cached_settings  # noqa: PLC2701

    _cached_settings.cache_clear()

    test_app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def remote_client() -> AsyncIterator[AsyncClient]:
    """Return an async HTTPX client pointing at a remote/live test environment."""
    async with AsyncClient(base_url=_remote_base_url(), timeout=30) as client:
        yield client


@pytest_asyncio.fixture
async def app_client(memory_client: AsyncClient) -> AsyncClient:
    """Backward-compatible alias for in-memory API tests."""
    return memory_client


@pytest.fixture
def api_key_header() -> dict[str, str]:
    """Return headers containing the test API key.

    Returns:
        Dict with X-API-Key header.
    """
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def remote_api_key_header() -> dict[str, str]:
    """Return headers containing the API key for remote/live tests."""
    return {"X-API-Key": _remote_api_key()}


@pytest.fixture
def correlation_id_header() -> dict[str, str]:
    """Return headers containing a fixed correlation ID for tests.

    Returns:
        Dict with X-Correlation-ID header.
    """
    return {"X-Correlation-ID": "test-correlation-id"}
