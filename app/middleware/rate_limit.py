"""Rate limiting middleware — fixed-window in-memory counter per client key."""

from __future__ import annotations

import math
import time
from collections.abc import Awaitable, Callable

from app.api.deps import maybe_get_current_user
from petstore_core.config import Settings, get_settings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

#: Paths that are exempt from rate limiting (mirrors the auth exemptions).
EXEMPT_PATHS = {"/health", "/api/v1/health", "/redoc", "/openapi.json"}

#: Header name used to bypass rate limiting.
BYPASS_HEADER = "X-Bypass-Key"

RATE_LIMIT_LIMIT_HEADER = "X-RateLimit-Limit"
RATE_LIMIT_REMAINING_HEADER = "X-RateLimit-Remaining"
RATE_LIMIT_RESET_HEADER = "X-RateLimit-Reset"


def _get_client_key(request: Request) -> str:
    """Return a stable key that identifies the calling client.

    Prefers the authenticated user identifier when available; otherwise falls
    back to the client IP address extracted from ``X-Forwarded-For`` or the
    direct connection address.

    Args:
        request: The incoming HTTP request.

    Returns:
        A string key in the form ``"user:<value>"`` or ``"ip:<address>"``.
    """
    app = request.scope.get("app")
    state = getattr(app, "state", None)
    settings = getattr(state, "settings", None)
    auth_settings = settings if isinstance(settings, Settings) else get_settings()
    user = maybe_get_current_user(request, settings=auth_settings)
    if user is not None and user.id is not None:
        return f"user:{user.id}"

    forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if forwarded_for:
        return f"ip:{forwarded_for}"

    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def _seconds_until_reset(window_start: float, window_seconds: int, now: float) -> int:
    """Return the number of whole seconds until the current window resets."""
    remaining = window_seconds - (now - window_start)
    return max(0, math.ceil(remaining))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window in-memory rate limiter for all non-exempt routes.

    Each unique client key (authenticated user ID or IP address) is allowed up to
    ``max_requests`` requests within a fixed ``window_seconds`` window.
    Once the counter exceeds the limit a ``429 Too Many Requests`` response
    is returned with a ``Retry-After`` header.

    Requests that supply the correct ``X-Bypass-Key`` header value skip rate
    limiting entirely, regardless of how many requests have been made.

    Args:
        app: The ASGI application to wrap.
        max_requests: Maximum number of requests allowed per window.
        window_seconds: Duration of the rate-limit window in seconds.
        bypass_key: Secret header value that disables rate limiting.
            An empty string disables the bypass mechanism.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int,
        window_seconds: int,
        bypass_key: str,
    ) -> None:
        """Initialise the middleware.

        Args:
            app: The downstream ASGI application.
            max_requests: Maximum requests per window per client key.
            window_seconds: Window duration in seconds.
            bypass_key: Value that, when supplied in ``X-Bypass-Key``, skips
                the rate limit check.  Empty string means no bypass is active.
        """
        super().__init__(app)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._bypass_key = bypass_key
        # Per-instance counter: client_key -> (count, window_start_timestamp)
        self._counters: dict[str, tuple[int, float]] = {}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Apply rate limiting logic before forwarding the request.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to invoke the next middleware or route handler.

        Returns:
            The downstream response, or a ``429`` response when the limit is
            exceeded.
        """
        # Exempt well-known paths (health, docs, OpenAPI schema).
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        # Bypass: skip rate limiting when the correct secret header is present.
        if self._bypass_key and request.headers.get(BYPASS_HEADER, "") == self._bypass_key:
            return await call_next(request)

        client_key = _get_client_key(request)
        now = time.time()

        count, window_start = self._counters.get(client_key, (0, now))

        if now - window_start >= self._window_seconds:
            # Window has elapsed — start a fresh one.
            count = 1
            window_start = now
        else:
            count += 1

        self._counters[client_key] = (count, window_start)

        reset_seconds = _seconds_until_reset(window_start, self._window_seconds, now)

        if count > self._max_requests:
            retry_after = max(1, reset_seconds)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry after the window resets."},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers[RATE_LIMIT_LIMIT_HEADER] = str(self._max_requests)
        response.headers[RATE_LIMIT_REMAINING_HEADER] = str(max(0, self._max_requests - count))
        response.headers[RATE_LIMIT_RESET_HEADER] = str(reset_seconds)
        return response
