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


async def supabase_sign_up(
    email: str,
    password: str,
    *,
    metadata: dict[str, Any] | None = None,
    settings: Settings,
) -> dict[str, Any]:
    """Register a new user account via Supabase Auth.

    Calls ``POST {supabase_url}/auth/v1/signup``.

    Args:
        email: The new user's email address.
        password: The new user's password.
        metadata: Optional ``user_metadata`` payload (username, first_name, etc.)
            stored on the Supabase user record.
        settings: Application settings; must have ``supabase_url`` and
            ``supabase_anon_key`` set.

    Returns:
        Supabase user payload dict. When email confirmation is disabled the dict
        includes ``id`` (UUID), ``email``, and ``user_metadata``.

    Raises:
        SupabaseAuthNotConfiguredError: If required Supabase settings are missing.
        HTTPException 409: If the email address is already registered.
        HTTPException 422: If the payload is invalid (e.g. weak password).
        HTTPException 503: If the Supabase Auth service is unreachable.
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise SupabaseAuthNotConfiguredError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set for staging/prod signup."
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/signup"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {"email": email, "password": password}
    if metadata:
        body["data"] = metadata

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=body, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth service is unreachable.",
        ) from exc

    if response.status_code == 400:
        detail = response.json().get("msg") or response.json().get("message") or "Bad request."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if response.status_code == 422:
        detail = response.json().get("msg") or response.json().get("message") or "Invalid request."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    # Supabase returns 200 even for duplicate emails (with empty identity array).
    # Detect this case: response has an id but identities list is empty.
    if response.status_code == 200:
        data = cast(dict[str, Any], response.json())
        identities = data.get("identities")
        if isinstance(identities, list) and len(identities) == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists.",
            )
        return data

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Supabase Auth returned an unexpected error ({response.status_code}).",
    )


async def supabase_update_user(
    access_token: str,
    *,
    email: str | None = None,
    phone: str | None = None,
    metadata: dict[str, Any] | None = None,
    settings: Settings,
) -> dict[str, Any]:
    """Update the authenticated user's profile in Supabase Auth.

    Calls ``PUT {supabase_url}/auth/v1/user`` with the user's own bearer token.

    Args:
        access_token: The user's current bearer token (from their Supabase session).
        email: New email address, if changing.
        phone: New phone number, if changing.
        metadata: Optional ``user_metadata`` fields to merge.
        settings: Application settings; must have ``supabase_url`` and
            ``supabase_anon_key`` set.

    Returns:
        Updated Supabase user payload dict.

    Raises:
        SupabaseAuthNotConfiguredError: If required Supabase settings are missing.
        HTTPException 422: If the payload is invalid.
        HTTPException 503: If the Supabase Auth service is unreachable.
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise SupabaseAuthNotConfiguredError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set for staging/prod user updates."
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {}
    if email is not None:
        body["email"] = email
    if phone is not None:
        body["phone"] = phone
    if metadata is not None:
        body["data"] = metadata

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(url, json=body, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth service is unreachable.",
        ) from exc

    if response.status_code == 422:
        detail = response.json().get("msg") or response.json().get("message") or "Invalid request."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase Auth returned an unexpected error ({response.status_code}).",
        )

    return cast(dict[str, Any], response.json())


async def supabase_delete_user(
    user_uuid: str,
    *,
    settings: Settings,
) -> None:
    """Permanently delete a user from Supabase Auth using the service role key.

    Calls ``DELETE {supabase_url}/auth/v1/admin/users/{uuid}``.

    Args:
        user_uuid: The Supabase user UUID to delete.
        settings: Application settings; must have ``supabase_url`` and
            ``supabase_service_role_key`` set.

    Raises:
        SupabaseAuthNotConfiguredError: If the service role key is missing.
        HTTPException 404: If the user does not exist in Supabase.
        HTTPException 503: If the Supabase Auth service is unreachable.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SupabaseAuthNotConfiguredError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for admin user deletion."
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_uuid}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth service is unreachable.",
        ) from exc

    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in Supabase Auth.",
        )

    if response.status_code not in (200, 204):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase Auth returned an unexpected error ({response.status_code}).",
        )


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
