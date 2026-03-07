"""Auth middleware — validate X-API-Key on all protected routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

#: Paths that are exempt from API key validation.
EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


def verify_credentials(token: str, expected: str) -> bool:
    """Validate an API key or token.

    Designed as a drop-in replacement point for JWT validation.

    Args:
        token: The credential supplied by the client.
        expected: The expected valid credential.

    Returns:
        True if the token is valid, False otherwise.
    """
    return token == expected


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Validate the X-API-Key header on all non-exempt routes.

    Args:
        app: The ASGI application to wrap.
        api_key: The expected API key value.
    """

    def __init__(self, app: ASGIApp, api_key: str) -> None:
        """Initialise the middleware.

        Args:
            app: The downstream ASGI application.
            api_key: The valid API key.
        """
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Validate the API key on protected routes.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to invoke the next middleware/handler.

        Returns:
            401 response if key is missing/invalid; else the downstream response.
        """
        # Allow exempt paths
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        if not verify_credentials(key, self._api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
