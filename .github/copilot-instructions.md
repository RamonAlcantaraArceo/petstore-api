# Petstore API — Copilot Context

This is a production-ready Python backend API implementing the Petstore OpenAPI 3.0 spec.

## Stack
- **Python 3.14**, FastAPI, Uvicorn
- **Storage**: In-memory dict (default), local PostgreSQL, or AWS RDS (via `STORAGE_MODE` env var)
- **ORM**: SQLAlchemy 2.x async with asyncpg driver
- **Config**: Pydantic Settings (env vars, `.env` file)
- **Logging**: structlog (JSON output, correlation ID propagation)
- **Auth**: API key via `X-API-Key` header; JWT-ready via `verify_credentials()`
- **Testing**: pytest + pytest-asyncio, factory_boy, Faker
- **Linting**: ruff + black; **Types**: mypy --strict

## Key Conventions
- All DB operations are `async/await`
- Repository pattern: Protocol-based abstractions in `app/repositories/base.py`
- Services delegate all persistence to repositories
- In-memory mode: zero external deps, state lost on restart
- Google-style docstrings on all public functions/classes
- Tests in `tests/unit/`, `tests/integration/`, `tests/system/`, `tests/e2e/`
- Performance tests in `performance/` — NOT run in CI
