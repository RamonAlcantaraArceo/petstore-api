"""Unit tests for package version exposure."""

from __future__ import annotations

import importlib
import importlib.metadata

import allure
import pytest

import app

pytestmark = [allure.epic("Application"), allure.feature("Configuration"), allure.severity(allure.severity_level.TRIVIAL)]

def test_version_comes_from_distribution_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expose package version from installed distribution metadata."""
    monkeypatch.setattr("importlib.metadata.version", lambda _: "1.2.3")

    reloaded = importlib.reload(app)

    assert reloaded.__version__ == "1.2.3"


def test_version_falls_back_when_distribution_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback to a safe default when package metadata is unavailable."""

    def _raise_package_not_found(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", _raise_package_not_found)

    reloaded = importlib.reload(app)

    assert reloaded.__version__ == "0.0.0"
