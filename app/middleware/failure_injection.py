"""Failure injection middleware for demo/testing purposes."""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class FailureInjectionMiddleware(BaseHTTPMiddleware):
    """Injects random failures into requests for demo and testing purposes.

    When enabled, this middleware randomly returns 500, 503, or 504 errors
    with a configurable probability. Useful for simulating transient failures
    and demonstrating resilience during demos.

    Args:
        app: The ASGI application to wrap.
        probability: Float between 0.0 and 1.0 indicating the probability
            of injecting a failure. For example, 0.1 means ~10% of requests fail.
    """

    FAILURE_STATUSES = [500, 503, 504]
    FAILURE_MESSAGES = {
        500: "Internal Server Error (injected failure)",
        503: "Service Unavailable (injected failure)",
        504: "Gateway Timeout (injected failure)",
    }

    def __init__(self, app: ASGIApp, probability: float) -> None:
        """Initialise the middleware.

        Args:
            app: The downstream ASGI application.
            probability: Failure injection probability (0.0-1.0).
        """
        super().__init__(app)
        self._probability = max(0.0, min(1.0, probability))

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Randomly inject failures before forwarding the request.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to invoke the next middleware or route handler.

        Returns:
            Either a failure response (if injection triggered) or the downstream
            response.
        """
        if random.random() < self._probability:
            status_code = random.choice(self.FAILURE_STATUSES)
            message = self.FAILURE_MESSAGES[status_code]
            logger = structlog.get_logger()
            logger.warning(
                "failure_injected",
                path=request.url.path,
                method=request.method,
                status_code=status_code,
            )
            return JSONResponse(
                status_code=status_code,
                content={"detail": message},
            )

        return await call_next(request)
