"""Correlation ID middleware — inject, generate, and propagate X-Correlation-ID."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

CORRELATION_ID_HEADER = "X-Correlation-ID"

#: Context variable holding the current request's correlation ID.
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Read or generate X-Correlation-ID for every request and echo it in the response.

    Args:
        app: The ASGI application to wrap.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialise the middleware.

        Args:
            app: The downstream ASGI application.
        """
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process a request, ensuring a correlation ID is set.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to invoke the next middleware/handler.

        Returns:
            The HTTP response with X-Correlation-ID header attached.
        """
        cid = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        correlation_id_var.set(cid)

        response: Response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = cid
        return response
