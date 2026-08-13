"""FastAPI application factory, middleware registration, and lifespan."""

from __future__ import annotations

import logging
import sys
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import deepcopy

import structlog
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from petstore_core.config import get_settings

from app.api.v1.health import router as health_router
from app.api.v1.router import router as v1_router
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.rate_limit import BYPASS_HEADER, RateLimitMiddleware

warnings.filterwarnings("error", message="Duplicate Operation ID")


def configure_logging(log_level: str, app_env: str) -> None:
    """Configure application and standard-library logs through structlog.

    Args:
        log_level: The log level string (e.g. "INFO").
        app_env: The application environment (e.g. "dev").
    """
    from app.middleware.correlation_id import correlation_id_var

    def add_service_context(
        logger: object, method: str, event_dict: structlog.types.EventDict
    ) -> structlog.types.EventDict:
        """Add request and service context to every log entry.

        Args:
            logger: The structlog logger.
            method: The logging method name.
            event_dict: The current log event dict.

        Returns:
            The event dict with service context added.
        """
        correlation_id = correlation_id_var.get("")
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
        event_dict["app_env"] = app_env
        event_dict["service"] = "petstore-api"
        return event_dict

    level = getattr(logging, log_level.upper(), logging.INFO)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_service_context,
        structlog.processors.add_log_level,
        # structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
    ]
    renderer: structlog.types.Processor
    if app_env == "dev":
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty(), sort_keys=True)
    else:
        renderer = structlog.processors.JSONRenderer(sort_keys=True)

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Uvicorn installs dedicated handlers before importing the app. Route its
    # server and access records through the same correlation-aware formatter.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
        uvicorn_logger.setLevel(level)

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
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
        struct_logger = structlog.get_logger()

        if settings.rate_limit_bypass_key:
            struct_logger.info(
                "rate_limit_bypass_key_configured",
                bypass_key_length=len(settings.rate_limit_bypass_key),
            )

        else:
            struct_logger.info("rate_limit_bypass_disabled")

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
            "use `POST /api/v1/user/auth` with a seeded username to obtain a "
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

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """Root endpoint redirecting to API docs."""
        return RedirectResponse(url="/docs", status_code=308)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> PlainTextResponse:
        return PlainTextResponse("😢 404 Not Found", status_code=404)

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

    # Starlette executes the most recently added middleware first.
    if settings.failure_injection_enabled:
        from app.middleware.failure_injection import FailureInjectionMiddleware

        app.add_middleware(
            FailureInjectionMiddleware,
            probability=settings.failure_injection_probability,
        )

    if settings.delay_injection_enabled:
        from app.middleware.delay_injection import DelayInjectionMiddleware

        app.add_middleware(
            DelayInjectionMiddleware,
            probability=settings.delay_injection_probability,
            max_delay_seconds=settings.delay_injection_max_seconds,
        )

    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        bypass_key=settings.rate_limit_bypass_key,
    )
    app.add_middleware(CorrelationIdMiddleware)

    # Routes
    app.include_router(health_router)
    app.include_router(v1_router)

    return app


app = create_app()
