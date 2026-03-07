# Testing Guide

## Test Layers

| Layer | Directory | Description |
|---|---|---|
| Unit | `tests/unit/` | Service layer, mocked repositories |
| Integration | `tests/integration/` | HTTP-level, in-memory or testcontainers |
| System | `tests/system/` | Multi-step workflow tests |
| E2E | `tests/e2e/` | Live service smoke tests |
| Performance | `performance/` | pytest-benchmark (manual only) |

## Running Tests

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All CI tests with coverage
pytest tests/unit/ tests/integration/ tests/system/ --cov=app

# E2E against staging (requires E2E_BASE_URL)
E2E_BASE_URL=https://staging.example.com pytest tests/e2e/
```

## Coverage

Minimum 80% coverage is enforced in CI. Generate a report:

```bash
pytest tests/unit/ tests/integration/ tests/system/ \
  --cov=app --cov-report=html
open htmlcov/index.html
```
