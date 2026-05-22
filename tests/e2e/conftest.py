"""E2E-local Docker stack fixtures for coverage-enabled service tests."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from httpx import HTTPError, get

E2E_MODE = os.environ.get("E2E_MODE", "docker")
LOCAL_E2E_URL = "http://localhost:8000"

if E2E_MODE == "docker":
    # Set before collection hooks run so remote_only tests are not auto-skipped.
    os.environ["E2E_BASE_URL"] = LOCAL_E2E_URL
    os.environ["API_KEY"] = "test-api-key"


@pytest.fixture(scope="session")
def docker_compose_command() -> str:
    """Return compose command used by pytest-docker."""
    return "docker compose"


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig: pytest.Config) -> str:
    """Return docker compose file used for local E2E stack."""
    return str(Path(pytestconfig.rootpath) / "tests" / "e2e" / "docker-compose.e2e.yml")


def _is_healthy(url: str) -> bool:
    """Return True when health endpoint is responsive and healthy."""
    try:
        response = get(f"{url}/health", timeout=2)
        response.raise_for_status()
        return response.json().get("status") == "ok"
    except (HTTPError, ValueError):
        return False


@pytest.fixture(scope="session", autouse=True)
def e2e_docker_stack(
    docker_services: Any,
) -> Iterator[None]:
    """Bring up local E2E stack when E2E_MODE=docker."""
    if E2E_MODE != "docker":
        yield
        return

    docker_services.wait_until_responsive(
        timeout=180,
        pause=2,
        check=lambda: _is_healthy(LOCAL_E2E_URL),
    )
    yield

    with contextlib.suppress(Exception):
        docker_services._docker_compose.execute("kill -s USR2 api")
