"""FastAPI application factory, middleware registration, and lifespan."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.middleware.auth import ApiKeyMiddleware
from app.middleware.correlation_id import CorrelationIdMiddleware


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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    settings = get_settings()
    configure_logging(settings.log_level, settings.app_env)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Startup logic
        if settings.storage_mode != "memory":
            from app.db.session import ensure_db_schema, init_db

            init_db(settings)
            await ensure_db_schema()
        yield
        # (Optional) Add shutdown logic here if needed

    app = FastAPI(
        title="Petstore API",
        description="A production-ready Petstore API built with FastAPI.",
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Middleware (outermost first)
    app.add_middleware(ApiKeyMiddleware, api_key=settings.api_key)
    app.add_middleware(CorrelationIdMiddleware)

    # Routes
    app.include_router(v1_router)

    @app.get("/health", tags=["health"])
    async def health_check() -> JSONResponse:
        """Return service health status.

        Returns:
            JSON response with status and storage mode.
        """
        return JSONResponse({"status": "ok", "mode": settings.storage_mode})

    return app


app = create_app()
