"""Delay injection middleware for simulating slow responses."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class DelayInjectionMiddleware(BaseHTTPMiddleware):
    """Injects random delays into requests to simulate slow responses.

    When enabled, this middleware adds a random delay (up to a configured max)
    to a configurable percentage of requests. Useful for simulating network
    latency and demonstrating how clients handle slow responses during demos.

    Args:
        app: The ASGI application to wrap.
        probability: Float between 0.0 and 1.0 indicating the probability
            of injecting a delay. For example, 0.2 means ~20% of requests get delayed.
        max_delay_seconds: Maximum delay in seconds. Actual delay will be a
            random value between 0 and max_delay_seconds.
    """

    def __init__(
        self, app: ASGIApp, probability: float, max_delay_seconds: float
    ) -> None:
        """Initialise the middleware.

        Args:
            app: The downstream ASGI application.
            probability: Delay injection probability (0.0-1.0).
            max_delay_seconds: Maximum delay duration in seconds.
        """
        super().__init__(app)
        self._probability = max(0.0, min(1.0, probability))
        self._max_delay_seconds = max(0.0, max_delay_seconds)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Randomly inject delays before forwarding the request.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to invoke the next middleware or route handler.

        Returns:
            The downstream response, possibly with injected delay.
        """
        if random.random() < self._probability:
            delay = random.uniform(0.0, self._max_delay_seconds)
            logger = structlog.get_logger()
            logger.info(
                "delay_injected",
                path=request.url.path,
                method=request.method,
                delay_seconds=round(delay, 3),
            )
            await asyncio.sleep(delay)

        return await call_next(request)
