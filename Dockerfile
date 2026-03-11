# syntax=docker/dockerfile:1
# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency files first for layer caching
COPY pyproject.toml ./
RUN touch README.md

# Install production dependencies only (no dev extras)
RUN uv pip install --system --no-cache-dir -e . 2>/dev/null || \
    pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic-settings \
    "sqlalchemy[asyncio]" asyncpg alembic structlog httpx python-multipart

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

# Non-root user for security
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.14 /usr/local/lib/python3.14
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source only
COPY app/ ./app/

# Use non-root user
USER appuser

EXPOSE 8000

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
