"""FastAPI application factory, middleware registration, and lifespan."""

from __future__ import annotations

import logging
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import deepcopy

import structlog
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from petstore_core.config import get_settings

from app.api.routes.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.router import router as v1_router
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

warnings.filterwarnings("error", message="Duplicate Operation ID")


def configure_logging(log_level: str, app_env: str) -> None:
    """Configure structlog for structured JSON output.

    Args:
        log_level: The log level string (e.g. "INFO").
        app_env: The application environment (e.g. "dev").
    """
    from app.middleware.correlation_id import correlation_id_var

    def add_correlation_id(
        logger: object, method: str, event_dict: structlog.types.EventDict
    ) -> structlog.types.EventDict:
        """Add the current correlation ID to every log entry.

        Args:
            logger: The structlog logger.
            method: The logging method name.
            event_dict: The current log event dict.

        Returns:
            The event dict with correlation_id added.
        """
        event_dict["correlation_id"] = correlation_id_var.get("")
        event_dict["app_env"] = app_env
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_correlation_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.MODULE,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _first_forwarded_value(value: str | None) -> str | None:
    """Return first value from a comma-separated forwarded header."""
    if not value:
        return None
    return value.split(",", 1)[0].strip() or None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    settings = get_settings()
    configure_logging(settings.log_level, settings.app_env)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        # Startup logic
        if settings.storage_mode != "memory":
            from petstore_core.db.session import ensure_db_schema, init_db

            init_db(settings)
            await ensure_db_schema()

        if settings.seed_dataset:
            from app.fixtures.loader import seed_from_settings

            await seed_from_settings(settings)

        yield
        # (Optional) Add shutdown logic here if needed

    app = FastAPI(
        title="Petstore API",
        description=(
            "A production-ready Petstore API built with FastAPI.\n\n"
            "## Authentication\n\n"
            "Protected `/api/v1/*` endpoints use `BearerAuth` JWTs. In development, "
            "use `POST /auth/dev/login` with a seeded username to obtain a "
            "Supabase-shaped token.\n\n"
            "## Rate Limiting\n\n"
            "All endpoints (except `/health` and `/openapi.json`) are subject to a "
            "**fixed-window rate limit** of `RATE_LIMIT_REQUESTS` requests per "
            "`RATE_LIMIT_WINDOW_SECONDS` seconds (default: **40 req / 60 s**) "
            "per authenticated user ID or client IP.\n\n"
            "Accepted responses include `X-RateLimit-Limit`, "
            "`X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.\n\n"
            "When the limit is exceeded the API returns `429 Too Many Requests` with a "
            "`Retry-After` header indicating how many seconds to wait.\n\n"
            "### Bypass\n\n"
            "Include the `X-Bypass-Key` header with the value configured via the "
            "`RATE_LIMIT_BYPASS_KEY` environment variable to skip rate limiting entirely."
        ),
        version=settings.api_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
        contact={"name": "Ramon Alcantara Arceo", "email": "ramalc.ms@outlook.com"},
    )
    app.state.settings = settings

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_json(request: Request) -> JSONResponse:
        """Serve OpenAPI schema with dynamic server URL from the current request."""
        schema = get_openapi(
            title=app.title,
            description=app.description,
            version=app.version,
            routes=app.routes,
            contact=app.contact,
        )
        schema = deepcopy(schema)
        components = schema.setdefault("components", {})
        parameters = components.setdefault("parameters", {})
        parameters["BypassKeyHeader"] = {
            "name": BYPASS_HEADER,
            "in": "header",
            "required": False,
            "schema": {"type": "string"},
            "description": (
                "Optional header that bypasses rate limiting when it matches "
                "`RATE_LIMIT_BYPASS_KEY`."
            ),
        }
        for path, path_item in schema.get("paths", {}).items():
            if path in {"/health", "/api/v1/health", "/openapi.json"} or path.startswith("/docs"):
                continue
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                parameters_list = operation.setdefault("parameters", [])
                if not any(
                    isinstance(parameter, dict)
                    and (
                        parameter.get("$ref") == "#/components/parameters/BypassKeyHeader"
                        or parameter.get("name") == BYPASS_HEADER
                    )
                    for parameter in parameters_list
                ):
                    parameters_list.append({"$ref": "#/components/parameters/BypassKeyHeader"})
        forwarded_proto = _first_forwarded_value(request.headers.get("x-forwarded-proto"))
        forwarded_host = _first_forwarded_value(request.headers.get("x-forwarded-host"))
        scheme = forwarded_proto or request.url.scheme
        host = forwarded_host or request.headers.get("host", request.url.netloc)
        schema["servers"] = [{"url": f"{scheme}://{host}"}]
        return JSONResponse(schema)

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_html() -> object:
        """Serve Swagger UI pointing to the custom OpenAPI endpoint."""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html() -> object:
        """Serve ReDoc pointing to the custom OpenAPI endpoint."""
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - ReDoc",
        )

    # Middleware (outermost first)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        bypass_key=settings.rate_limit_bypass_key,
    )

    # Routes
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(v1_router)

    return app


app = create_app()
