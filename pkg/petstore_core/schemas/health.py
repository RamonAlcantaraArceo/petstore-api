"""Pydantic schemas for health responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthDetails(BaseModel):
    """Additional health metadata.

    Attributes:
        version: Application version.
        build_date: Build date string.
        git_commit_sha: Git commit SHA.
    """

    version: str
    build_date: str
    git_commit_sha: str


class HealthResponse(BaseModel):
    """Health check response payload.

    Attributes:
        status: Service status string.
        mode: Storage mode.
        details: Build and version metadata.
    """

    status: Literal["ok"]
    mode: str
    details: HealthDetails
