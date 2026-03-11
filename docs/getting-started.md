# Getting Started

## Prerequisites

- Python 3.14+
- Docker & Docker Compose
- `uv` package manager

Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Local Development (In-Memory Mode)

```bash
# 1. Clone the repository
git clone https://github.com/RamonAlcantaraArceo/petstore-api.git
cd petstore-api

# 2. Copy env file and set your API key
cp .env.example .env
# Edit .env and set API_KEY=your-dev-key

# 3. Start the API
docker compose up

# 4. Test the health endpoint
curl http://localhost:8000/health
```

## Local Development (Python)

```bash
# Create a Python 3.14 environment and install dependencies
uv sync --python 3.14 --extra dev

# Set environment variables
export STORAGE_MODE=memory
export API_KEY=dev-api-key

# Start the server
uv run uvicorn app.main:app --reload
```

## Running Tests

```bash
# Unit tests
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/integration/

# System tests
uv run pytest tests/system/

# All tests with coverage
uv run pytest tests/unit/ tests/integration/ tests/system/ --cov=app
```
