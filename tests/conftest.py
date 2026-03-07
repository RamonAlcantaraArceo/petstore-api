"""Shared test fixtures — app client, service factories, and entity factories."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import reset_memory_repos
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_repos() -> None:
    """Reset all in-memory repositories before each test."""
    reset_memory_repos()


@pytest_asyncio.fixture
async def app_client() -> AsyncClient:
    """Return an async HTTPX client targeting the FastAPI test app (in-memory mode).

    Yields:
        AsyncClient connected to the test app.
    """
    import os

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


@pytest.fixture
def api_key_header() -> dict[str, str]:
    """Return headers containing the test API key.

    Returns:
        Dict with X-API-Key header.
    """
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def correlation_id_header() -> dict[str, str]:
    """Return headers containing a fixed correlation ID for tests.

    Returns:
        Dict with X-Correlation-ID header.
    """
    return {"X-Correlation-ID": "test-correlation-id"}
