# E2E Docker Coverage Guide

This guide explains the recent E2E testing changes and how to run the suite with coverage and Allure in a predictable way.

## What Changed

The E2E flow now supports a fixture-scoped local Docker stack so E2E tests can run against a real API + Postgres while still contributing coverage.

Implemented pieces:

- `tests/e2e/conftest.py`
  - Uses `pytest-docker` to spin up the E2E stack when `E2E_MODE=docker`.
  - Sets `E2E_BASE_URL=http://localhost:8000` and `API_KEY=test-api-key` for docker E2E mode.
  - Sends `USR2` to the API container at fixture teardown so coverage data is flushed.

- `tests/e2e/docker-compose.e2e.yml`
  - Defines `postgres` and `api` services for E2E execution.
  - Runs API under coverage:
    - `coverage run --parallel-mode --save-signal=USR2 -m uvicorn ...`
  - Writes service coverage files into `.e2e-coverage/` on the host.

- `pyproject.toml`
  - Added dev dependencies: `coverage`, `pytest-docker`.
  - Added `[tool.coverage.paths]` mapping for host/container path reconciliation.

- `.github/workflows/ci.yml`
  - Runs full tests including E2E (`tests/`) with `E2E_MODE=docker`.
  - Merges container coverage after pytest finishes.

## Local Execution

### 1. E2E only (docker-scoped stack)

Use this to verify E2E behavior only.

```bash
STORAGE_MODE=memory API_KEY=test-api-key E2E_MODE=docker \
uv run --extra dev pytest tests/e2e -q
```

Expected:

- E2E compose stack is started and torn down by fixtures.
- 3 E2E tests pass.
- `.e2e-coverage/.coverage.service*` files are produced.

### 2. Full suite with merged coverage (recommended)

```bash
docker compose -f tests/e2e/docker-compose.e2e.yml down -v
rm -rf .e2e-coverage .coverage coverage.xml

STORAGE_MODE=memory API_KEY=test-api-key E2E_MODE=docker \
uv run --extra dev pytest tests --cov=app --cov-fail-under=0 --cov-report=xml -q

uv run --extra dev coverage combine --append .e2e-coverage/.coverage.service*
uv run --extra dev coverage xml -o coverage.xml
uv run --extra dev coverage html -d htmlcov-combined
uv run --extra dev coverage report --fail-under=80
```

Expected:

- All tests pass.
- Coverage is merged from:
  - in-process pytest coverage
  - API container coverage files from `.e2e-coverage/`
- Final combined coverage should pass threshold (currently around mid 80s).

## CI Behavior

CI uses the same strategy:

1. Run all tests with coverage collection enabled.
2. Append merge service coverage artifacts from `.e2e-coverage/`.
3. Rebuild `coverage.xml`.
4. Enforce final threshold with `coverage report --fail-under=80`.

This avoids flaky ordering/timing problems from trying to merge coverage while pytest plugins are still finalizing files.

## Allure Notes

If you also want combined Allure output locally, run pytest with:

- `--alluredir=allure-results/`

Then generate report with:

```bash
allure generate allure-results -o allure-report
```

(If your local Allure CLI does not support `--clean`, omit that flag.)

## Troubleshooting

- 401 in E2E tests:
  - Ensure API key is `test-api-key` in docker mode.

- Coverage remains around 75 percent:
  - You likely skipped the post-pytest merge command:
    - `coverage combine --append .e2e-coverage/.coverage.service*`

- Port conflicts on 5432 or 8000:
  - Stop local containers/processes and rerun.

- E2E startup timeout:
  - Bring stack down and retry:
    - `docker compose -f tests/e2e/docker-compose.e2e.yml down -v`
