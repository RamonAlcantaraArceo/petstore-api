# E2E Coverage Guide

This guide explains how E2E tests run a real service in a separate process and
how their coverage data is merged with the in-process pytest coverage.

## How It Works

E2E tests need a live service to hit over HTTP. To still contribute to overall
coverage, the service is launched under `coverage run --parallel-mode` so that
each instrumented process writes its own `.coverage.*` file. After pytest
finishes, those files are merged into the combined coverage database.

Implementation:

- `tests/e2e/conftest.py`
  - Picks a free localhost port and exports `E2E_BASE_URL=http://127.0.0.1:<port>`
    and `API_KEY=test-api-key` at module import time so `tests/conftest.py`
    does not skip `remote_only` tests during collection.
  - Spawns a subprocess equivalent to:
    ```bash
    python -m coverage run --parallel-mode --save-signal=USR1 \
        --rcfile pyproject.toml \
        -m uvicorn app.main:app --host 127.0.0.1 --port <port>
    ```
    with `COVERAGE_FILE=.e2e-coverage/.coverage.service` so each forked
    worker writes uniquely-named files under `.e2e-coverage/`.
  - When Docker is available a `testcontainers` Postgres instance is started
    and the service runs with `STORAGE_MODE=local` against it (so the
    postgres repositories contribute to coverage). When Docker is not
    available the fixture falls back to `STORAGE_MODE=memory` so developers
    without Docker can still run E2E tests locally.
  - To force memory mode explicitly: `E2E_STORAGE_MODE=memory pytest tests/e2e`.
  - Waits for `/health` to return `status=ok` before yielding.
  - On teardown, sends `SIGUSR1` (the coverage `--save-signal`) so the
    instrumented process writes `.coverage.service.*` files, then sends
    `SIGTERM` for a clean uvicorn shutdown. (`atexit` handlers do not run
    when uvicorn's signal handler exits the process, so an explicit save
    signal is required.)
  - If `TEST_BASE_URL` or `E2E_BASE_URL` is already set by the caller, the
    fixture does **not** spawn anything and tests run against that target.

- `pyproject.toml`
  - `[tool.coverage.paths]` maps in-process and subprocess paths to the same
    canonical source tree so `coverage combine` reconciles them.

- `.github/workflows/ci.yml`
  - Runs the full suite (including `tests/e2e/`) with the local subprocess
    fixture, then appends the service coverage files and rebuilds `coverage.xml`.

## Why Not Docker?

The previous design used `docker compose` to run the API container with a
bind-mounted `.e2e-coverage/` volume. In CI the container ran as root and
produced root-owned coverage files; `coverage combine` (running as the
unprivileged GitHub Actions `runner` user) then failed with `PermissionError`
when trying to delete the merged source files. Running the service as a
host-side subprocess of the test runner sidesteps the entire UID-mapping
problem and removes the Docker dependency from CI.

## Local Execution

### 1. E2E only

```bash
uv run --extra dev pytest tests/e2e -q
```

Expected:

- A local `uvicorn` subprocess is started under `coverage` and torn down by the
  fixture.
- All E2E tests pass.
- `.e2e-coverage/.coverage.service.*` files are produced.

### 2. Full suite with merged coverage

```bash
rm -rf .e2e-coverage .coverage coverage.xml

uv run --extra dev pytest tests \
  --cov=app --cov-fail-under=0 --cov-report=xml -q

uv run --extra dev coverage combine --append .e2e-coverage/.coverage.service*
uv run --extra dev coverage xml -o coverage.xml
uv run --extra dev coverage html -d htmlcov-combined
uv run --extra dev coverage report --fail-under=80
```

Expected:

- All tests pass.
- Coverage is merged from in-process pytest runs **and** the E2E subprocess.
- Final combined coverage passes the threshold.

### 3. Running E2E against a remote environment

```bash
TEST_BASE_URL=https://staging.example.com API_KEY=... \
  uv run --extra dev pytest tests/e2e -q
```

The fixture detects the external URL and does not spawn a local service.

## Troubleshooting

- **401 in E2E tests:** Ensure `API_KEY=test-api-key` matches the value used by
  the spawned service (default in fixture).
- **Coverage stays around 75%:** Verify the post-pytest merge step ran:
  `coverage combine --append .e2e-coverage/.coverage.service*`.
- **Port conflict:** The fixture picks an ephemeral port automatically; ensure
  no firewall blocks `127.0.0.1` traffic.
- **Service never becomes healthy:** Inspect stdout/stderr from the subprocess
  (rerun with `LOG_LEVEL=INFO` and remove `--log-level warning` locally).
