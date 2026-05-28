# Petstore API

[![CI](https://github.com/RamonAlcantaraArceo/petstore-api/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonAlcantaraArceo/petstore-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![codecov](https://codecov.io/gh/RamonAlcantaraArceo/petstore-api/graph/badge.svg?token=YFYLQ5MLEO)](https://codecov.io/gh/RamonAlcantaraArceo/petstore-api)

A **production-ready Python backend API** implementing the [Petstore OpenAPI 3.0 spec](https://petstore3.swagger.io/api/v3/openapi.json), built with FastAPI.

## Package split

Core domain and persistence code now lives in `petstore_core/` (framework-agnostic), while
`app/` contains HTTP adapter concerns (routes, middleware, and FastAPI wiring).

## Quick Start


```bash
# Start the API in in-memory mode (no external dependencies required)
docker compose up

# Test it
curl http://localhost:8000/health
# {"status": "ok", "mode": "memory"}

curl -H "X-API-Key: dev-api-key" http://localhost:8000/api/v1/pet/findByStatus?status=available
```

## UV Workflow

This project uses [**uv**](https://docs.astral.sh/uv/) for fast dependency management and Python version handling.

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and set up the project
git clone https://github.com/RamonAlcantaraArceo/petstore-api.git
cd petstore-api

# Create a virtual environment and install dependencies
uv venv --seed --python 3.14 .venv  # Create a virtual environment
uv sync --all-extras  # Install all dependencies

# Run the dev server
uv run uvicorn app.main:app --reload

# Add a new dependency (e.g., requests)
uv add requests

# Add a dev-only dependency (e.g., ipython)
uv add --dev ipython

# Run any project command
uv run <command>  # e.g., uv run pytest, uv run ruff check .
```

## Environment Variables

| Variable       | Default       | Description                                  |
|----------------|---------------|----------------------------------------------|
| `STORAGE_MODE` | `memory`      | Runtime mode: `memory` \| `local` \| `cloud` |
| `API_KEY`      | `dev-api-key` | API key for authentication                   |
| `DATABASE_URL` | —             | PostgreSQL connection URL                    |
| `APP_ENV`      | `dev`         | Environment: `dev` \| `staging` \| `prod`    |
| `LOG_LEVEL`    | `INFO`        | Log level                                    |

## Running Tests

```bash
# Run test suites
uv run pytest tests/unit/ tests/integration/ tests/system/ --cov=app --cov=petstore_core

# Reproduce CI merge cleanup locally (lint + type-check + tests + reports)
make merge-cleanup
```

## Building and Deploying

```bash
# Build Docker image
docker build --target runtime -t petstore-api:latest .

# Deploy to Fly.io dev (uses latest GHCR image)
gh workflow run deploy-fly-dev.yml

# Deploy a specific version to Fly.io dev
gh workflow run deploy-fly-dev.yml -f version=v1.2.3

# Deploy to Fly.io staging
gh workflow run "Deploy to Fly.io Staging" -f version=v1.2.3
```

See [docs/deployment.md](docs/deployment.md) for full details, including PR review apps.

## Releases & Versioning

- Package version is derived from Git tags via Hatchling VCS (`vX.Y.Z` -> `X.Y.Z`).
- Docker images published to GHCR are tagged from the same Git tag (`vX.Y.Z`).
- We keep Python artifact release and GHCR image publishing as separate workflows for clearer logs and independent failure isolation.

### Cut a release

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

### Prereleases

```bash
git tag vX.Y.Z-beta.1
git push origin vX.Y.Z-beta.1

git tag vX.Y.Z-rc.1
git push origin vX.Y.Z-rc.1
```

## Documentation

📖 [Full documentation](https://ramonalcantaraarceo.github.io/petstore-api/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
