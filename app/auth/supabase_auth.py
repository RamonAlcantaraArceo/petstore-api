"""Supabase Auth REST API helpers for sign-in and sign-out."""

from __future__ import annotations

from typing import Any, cast

import httpx
from fastapi import HTTPException, status
from petstore_core.config import Settings


class SupabaseAuthNotConfiguredError(Exception):
    """Raised when Supabase Auth settings are missing."""


async def supabase_sign_in(
    email: str,
    password: str,
    *,
    settings: Settings,
) -> dict[str, Any]:
    """Authenticate a user against Supabase Auth and return the token payload.

    Calls ``POST {supabase_url}/auth/v1/token?grant_type=password``.

    Args:
        email: The user's email address (passed as the ``username`` query param
            in the Petstore login endpoint).
        password: The user's password.
        settings: Application settings; must have ``supabase_url`` and
            ``supabase_anon_key`` set.

    Returns:
        Supabase token response dict with at least ``access_token`` and
        ``token_type`` keys.

    Raises:
        SupabaseAuthNotConfiguredError: If required Supabase settings are missing.
        HTTPException 401: If Supabase rejects the credentials.
        HTTPException 503: If the Supabase Auth service is unreachable.
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise SupabaseAuthNotConfiguredError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set for staging/prod login."
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"email": email, "password": password},
                headers=headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth service is unreachable.",
        ) from exc

    if response.status_code == 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase Auth returned an unexpected error ({response.status_code}).",
        )

    return cast(dict[str, Any], response.json())


async def supabase_sign_out(
    access_token: str,
    *,
    settings: Settings,
) -> None:
    """Revoke a Supabase Auth session.

    Calls ``POST {supabase_url}/auth/v1/logout``.

    Args:
        access_token: The bearer token to revoke.
        settings: Application settings; must have ``supabase_url`` and
            ``supabase_anon_key`` set.

    Raises:
        SupabaseAuthNotConfiguredError: If required Supabase settings are missing.
        HTTPException 503: If the Supabase Auth service is unreachable.
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise SupabaseAuthNotConfiguredError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set for staging/prod logout."
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/logout"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth service is unreachable.",
        ) from exc
