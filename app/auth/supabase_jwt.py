"""Placeholder Supabase JWT validation helpers for staging and production."""

from __future__ import annotations

from typing import Any

from petstore_core.config import Settings


class SupabaseJWTError(Exception):
    """Raised when a Supabase JWT cannot be validated."""


class SupabaseJWTNotConfiguredError(SupabaseJWTError):
    """Raised when Supabase JWT validation has not been implemented yet."""


def validate_supabase_jwt(token: str, *, settings: Settings) -> dict[str, Any]:
    """Validate a Supabase JWT and return its claims.

    This is a stub for future JWKS-backed validation in staging and production.
    """
    del token, settings
    raise SupabaseJWTNotConfiguredError(
        "Supabase JWT validation is not configured yet."
    )
