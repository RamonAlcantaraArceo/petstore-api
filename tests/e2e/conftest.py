"""E2E fixtures spawning a local API subprocess under coverage.

The previous implementation booted the API via ``docker compose`` and shared
``.e2e-coverage/`` with the container as a bind-mounted volume. In CI, the
container ran as ``root`` and produced root-owned ``.coverage.service.*``
files; the subsequent host-side ``coverage combine`` then failed with
``PermissionError`` because the GitHub Actions ``runner`` user could not
delete those files (see PR #42 CI failure).

We now spawn ``uvicorn`` as a subprocess of the test session, instrumented
with ``coverage run --parallel-mode``. The coverage data files are owned by
the same user that runs ``coverage combine`` later, eliminating the
permission problem and removing the Docker dependency from E2E execution.

Behaviour:
    * If ``TEST_BASE_URL`` or ``E2E_BASE_URL`` is set by the caller, the
      fixture honors it and does **not** spawn a local service (the suite
      runs against the configured remote environment).
    * Otherwise, the fixture picks an ephemeral port, sets
      ``E2E_BASE_URL`` for ``tests/conftest.py`` collection hooks, and
      starts ``coverage run -m uvicorn app.main:app``. When Docker is
      available a `testcontainers` Postgres backend is provisioned so the
      postgres repositories also contribute to coverage; otherwise the
      service falls back to ``STORAGE_MODE=memory``.
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from httpx import HTTPError, get

LOCAL_API_KEY = "test-api-key"
HEALTH_TIMEOUT_SECONDS = 30.0
SHUTDOWN_TIMEOUT_SECONDS = 15.0

# Honor an externally configured target (deployed staging, etc.) without
# spawning anything locally.
_EXTERNAL_BASE_URL = os.environ.get("TEST_BASE_URL") or os.environ.get("E2E_BASE_URL")


def _pick_free_port() -> int:
    """Return an ephemeral TCP port bound momentarily on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


# Resolve the local base URL eagerly (at import time) so that
# ``tests/conftest.py::pytest_collection_modifyitems`` — which inspects
# ``E2E_BASE_URL`` to decide whether to skip ``remote_only`` tests — sees a
# usable value before collection runs.
if not _EXTERNAL_BASE_URL:
    _LOCAL_PORT = _pick_free_port()
    _LOCAL_BASE_URL = f"http://127.0.0.1:{_LOCAL_PORT}"
    os.environ["E2E_BASE_URL"] = _LOCAL_BASE_URL
    os.environ.setdefault("API_KEY", LOCAL_API_KEY)
else:
    _LOCAL_PORT = 0
    _LOCAL_BASE_URL = ""


def _is_healthy(url: str) -> bool:
    """Return True when the health endpoint responds with ``status=ok``."""
    try:
        response = get(f"{url}/health", timeout=2.0)
        response.raise_for_status()
        return bool(response.json().get("status") == "ok")
    except HTTPError, ValueError:
        return False


def _wait_until_ready(url: str, timeout: float) -> None:
    """Block until the service at ``url`` is healthy or raise on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_healthy(url):
            return
        time.sleep(0.25)
    raise RuntimeError(f"E2E service at {url} did not become healthy within {timeout}s")


@pytest.fixture(scope="session", autouse=True)
def e2e_local_service() -> Iterator[None]:
    """Start a local uvicorn subprocess under coverage for the E2E session.

    Yields control after the API reports healthy, then asks coverage to flush
    its data file (``SIGUSR1``) before sending ``SIGTERM`` for a clean
    uvicorn shutdown. The resulting ``.coverage.service.*`` files in
    ``.e2e-coverage/`` are owned by the test-runner user and can be merged
    later with ``coverage combine`` without any privilege issues.

    When Docker is available the service runs against a `testcontainers`
    PostgreSQL instance (`STORAGE_MODE=local`) so the postgres repositories
    contribute to coverage. Otherwise it falls back to `STORAGE_MODE=memory`.
    """
    if _EXTERNAL_BASE_URL:
        # Running against a pre-existing deployment; nothing to spawn.
        yield
        return

    repo_root = Path(__file__).resolve().parents[2]
    coverage_dir = repo_root / ".e2e-coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    storage_env, postgres_container = _start_postgres_or_memory()

    env = os.environ.copy()
    env.update(
        {
            "API_KEY": LOCAL_API_KEY,
            "APP_ENV": "dev",
            "LOG_LEVEL": "WARNING",
            # `coverage run --parallel-mode` appends a unique suffix per
            # process, producing files like `.coverage.service.<host>.<pid>...`.
            "COVERAGE_FILE": str(coverage_dir / ".coverage.service"),
            "PYTHONUNBUFFERED": "1",
            **storage_env,
        }
    )

    cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--parallel-mode",
        # Coverage's atexit hook does **not** fire when the process is killed
        # by a signal (uvicorn's SIGTERM handler does not run atexit). Bind a
        # dedicated "save" signal so the fixture can force a flush before
        # asking uvicorn to shut down.
        "--save-signal=USR1",
        "--rcfile",
        str(repo_root / "pyproject.toml"),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(_LOCAL_PORT),
        "--log-level",
        "warning",
    ]

    process = subprocess.Popen(  # noqa: S603 - command is built from trusted constants
        cmd,
        cwd=str(repo_root),
        env=env,
    )
    try:
        _wait_until_ready(_LOCAL_BASE_URL, HEALTH_TIMEOUT_SECONDS)
        yield
    finally:
        if process.poll() is None:
            # 1) Ask coverage to flush its data file before uvicorn exits.
            with contextlib.suppress(ProcessLookupError):
                process.send_signal(signal.SIGUSR1)
            # Give coverage a brief moment to write the file.
            time.sleep(1.0)
            # 2) Ask uvicorn to shut down gracefully.
            with contextlib.suppress(ProcessLookupError):
                process.send_signal(signal.SIGTERM)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
            if process.poll() is None:
                process.kill()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=5)
        if postgres_container is not None:
            with contextlib.suppress(Exception):
                postgres_container.stop()


def _start_postgres_or_memory() -> tuple[dict[str, str], Any | None]:
    """Provision a Postgres backend for the E2E service when feasible.

    Returns:
        A tuple of ``(env_overrides, container)`` where ``env_overrides`` is
        the set of environment variables to pass to the spawned uvicorn
        subprocess, and ``container`` is the running ``testcontainers``
        Postgres instance (or ``None`` when falling back to memory storage).

    Falls back to ``STORAGE_MODE=memory`` if Docker / testcontainers are not
    available so the suite can still run on developer laptops without Docker.
    """
    if os.environ.get("E2E_STORAGE_MODE", "").lower() == "memory":
        return {"STORAGE_MODE": "memory"}, None

    try:
        from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]
    except ImportError:
        return {"STORAGE_MODE": "memory"}, None

    try:
        container = PostgresContainer("postgres:16-alpine").start()
    except Exception:
        # Docker not available or image pull failed — fall back gracefully.
        return {"STORAGE_MODE": "memory"}, None

    database_url = container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    return (
        {"STORAGE_MODE": "local", "DATABASE_URL": database_url},
        container,
    )
