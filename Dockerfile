# syntax=docker/dockerfile:1

# ═══════════════════════════════════════════════════════════════════════════
# Petstore API - Production-Optimized Dockerfile
# ═══════════════════════════════════════════════════════════════════════════
#
# Multi-stage build with security hardening and minimal footprint
# Base image: python:3.14-slim
# Runtime user: appuser (UID 1001, non-root)
# Security: read-only filesystem, capability dropping, health checks
#
# Build: docker build --target runtime -t petstore-api:latest .
# Run:   docker run -p 8000:8000 -e STORAGE_MODE=memory petstore-api:latest
#
# ═══════════════════════════════════════════════════════════════════════════

# Build arguments
ARG PYTHON_VERSION=3.14
ARG UV_VERSION=0.4.29
ARG BUILD_DATE
ARG VERSION=0.1.0
ARG GIT_SHA=unknown

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder - Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

# Install system build dependencies (gcc needed for some Python packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install uv package manager with cache mount
ARG UV_VERSION
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir uv==${UV_VERSION}

# Copy only dependency files for layer caching
COPY pyproject.toml ./
RUN touch README.md

# Install production dependencies (no dev extras) with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache-dir -e .

# Verify critical runtime dependencies are present
RUN python -c "import sys; \
required = ['fastapi', 'uvicorn', 'pydantic_settings', 'sqlalchemy', 'asyncpg', 'alembic', 'structlog', 'httpx', 'python_multipart']; \
missing = [m for m in required if __import__('importlib.util', fromlist=['find_spec']).find_spec(m) is None]; \
print(f'ERROR: Missing modules: {missing}', file=sys.stderr) if missing else print('✓ All runtime dependencies verified successfully'); \
sys.exit(1 if missing else 0)"

# Compile Python bytecode for faster startup
RUN python -m compileall -b /usr/local/lib/python3.14/site-packages

# Remove development/test files from site-packages
RUN find /usr/local/lib/python3.14 -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.14 -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.14 -type f -name "*.pyo" -delete && \
    find /usr/local/lib/python3.14 -type d -name "__pycache__" -delete 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime - Minimal production image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

# Metadata labels (OCI Image Spec)
ARG VERSION
ARG BUILD_DATE
ARG GIT_SHA
LABEL org.opencontainers.image.title="Petstore API"
LABEL org.opencontainers.image.description="Production-ready FastAPI implementation of Petstore OpenAPI 3.0"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.vendor="Ramon Alcantara Arceo"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/RamonAlcantaraArceo/petstore-api"
LABEL org.opencontainers.image.documentation="https://ramonalcantaraarceo.github.io/petstore-api/"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.authors="ramonalcantaraarceo"
LABEL io.petstore.python.version="${PYTHON_VERSION}"

# Create non-root user and group with locked password and no shell
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -s /sbin/nologin -c "Application User" appuser && \
    mkdir -p /petstore /tmp/app && \
    chown -R appuser:appuser /tmp/app

WORKDIR /petstore

# Copy Python packages from builder (owned by root for immutability)
COPY --from=builder --chown=root:root /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

# Copy only required binaries (not entire /usr/local/bin)
COPY --from=builder --chown=root:root /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder --chown=root:root /usr/local/bin/alembic /usr/local/bin/alembic

# Copy application source code (owned by root for immutability)
COPY --chown=root:root app/ ./app/

# Compile application bytecode
RUN python -m compileall -b /petstore

# Remove pip, setuptools (not needed at runtime)
RUN pip uninstall -y pip setuptools 2>/dev/null || true

# Remove build tools and clean up apt cache to minimize image size and attack surface
RUN apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* /usr/bin/apt* /usr/bin/dpkg /usr/share/man /usr/share/doc
    #/usr/bin/gcc /usr/bin/cpp /usr/bin/make 

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TMPDIR=/tmp/app \
    PATH="/usr/local/bin:$PATH"

# Expose application port
EXPOSE 8000

# Health check using Python built-in urllib (no curl dependency)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Default command (can be overridden)
# Note: Use JSON array form for proper signal handling
ENTRYPOINT ["uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "30"]
