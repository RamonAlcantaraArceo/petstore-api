# Contributing

Thank you for contributing to Petstore API!

## Local Development Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/RamonAlcantaraArceo/petstore-api.git
cd petstore-api

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies (including dev extras)
pip install -e ".[dev]"

# 4. Set up pre-commit hooks
pre-commit install

# 5. Copy env file
cp .env.example .env
# Edit .env and set API_KEY
```

## Branch Naming

- Features: `feature/<description>`
- Bug fixes: `fix/<description>`
- Maintenance: `chore/<description>`

## Pull Request Process

1. Create a branch from `main`.
2. Make your changes and ensure all tests pass.
3. CI must pass (lint + type-check + test).
4. One reviewer approval required.
5. Squash and merge.

## Running the Full Test Suite

```bash
# Unit, integration, and system tests with coverage
pytest tests/unit/ tests/integration/ tests/system/ \
  --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Code Style

- **Formatting**: `black` (line length 100)
- **Linting**: `ruff`
- **Type checking**: `mypy --strict`
- **Docstrings**: Google style

Run all checks:

```bash
ruff check . && black --check . && mypy app/
```
