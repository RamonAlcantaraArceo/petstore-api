# Getting Started

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- `uv` package manager (optional)

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
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export STORAGE_MODE=memory
export API_KEY=dev-api-key

# Start the server
uvicorn app.main:app --reload
```

## Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# System tests
pytest tests/system/

# All tests with coverage
pytest tests/unit/ tests/integration/ tests/system/ --cov=app
```
