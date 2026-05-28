"""Domain-to-HTTP exception mapping helpers for API adapters."""

from __future__ import annotations

from collections.abc import Awaitable

from fastapi import HTTPException, status

from petstore_core.errors import DomainError, NotFoundError, ValidationError


async def map_domain_errors[T](call: Awaitable[T]) -> T:
    """Execute an awaitable and translate domain errors into HTTP exceptions."""
    try:
        return await call
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
