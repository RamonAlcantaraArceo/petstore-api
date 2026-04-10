# Petstore API

[![CI](https://github.com/RamonAlcantaraArceo/petstore-api/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonAlcantaraArceo/petstore-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **production-ready Python backend API** implementing the [Petstore OpenAPI 3.0 spec](https://petstore3.swagger.io/api/v3/openapi.json), built with FastAPI.

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
uv sync --python 3.14 --extra dev

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
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Use Python 3.14 and install dev dependencies
uv sync --python 3.14 --extra dev

# Run test suites
uv run pytest tests/unit/ tests/integration/ tests/system/ --cov=app
```

## Building and Deploying

```bash
# Build Docker image
docker build --target runtime -t petstore-api:latest .

# Deploy with Helm
helm upgrade --install petstore-api ./helm/petstore-api \
  -f ./helm/petstore-api/values-dev.yaml
```

## Documentation

📖 [Full documentation](https://ramonalcantaraarceo.github.io/petstore-api/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).