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

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `STORAGE_MODE` | `memory` | Runtime mode: `memory` \| `local` \| `cloud` |
| `API_KEY` | `dev-api-key` | API key for authentication |
| `DATABASE_URL` | — | PostgreSQL connection URL |
| `APP_ENV` | `dev` | Environment: `dev` \| `staging` \| `prod` |
| `LOG_LEVEL` | `INFO` | Log level |

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/unit/ tests/integration/ tests/system/ --cov=app
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