"""Health endpoint router shared across public and versioned paths."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.health import HealthDetails, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status.

    Returns:
        Typed health payload with runtime mode and build metadata.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        mode=settings.storage_mode,
        details=HealthDetails(**settings.details),
    )
