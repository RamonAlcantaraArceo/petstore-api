# Contributing

Thank you for contributing to Petstore API!

## Local Development Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/RamonAlcantaraArceo/petstore-api.git
cd petstore-api

# 2. Create a Python 3.14 environment and install dependencies
uv sync --python 3.14 --extra dev

# 3. Set up pre-commit hooks
uv run pre-commit install

# 4. Copy env file
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
uv run pytest tests/unit/ tests/integration/ tests/system/ \
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
uv run ruff check . && uv run black --check . && uv run mypy app/
```
