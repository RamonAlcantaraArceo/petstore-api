"""Unit tests for the application factory (create_app) and its middleware registration."""

from __future__ import annotations

import os

import allure
import pytest
from starlette.testclient import TestClient

pytestmark = [allure.epic("Application"), allure.feature("App Factory")]


def _clear_settings_cache() -> None:
    """Clear the cached settings to allow env-var changes to take effect."""
    from app.dependencies import _cached_settings  # noqa: PLC2701

    _cached_settings.cache_clear()


# ---------------------------------------------------------------------------
# Middleware registration
# ---------------------------------------------------------------------------


@allure.story("Middleware Registration")
@allure.severity(allure.severity_level.NORMAL)
def test_failure_injection_middleware_registered_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FailureInjectionMiddleware is added to the stack when the setting is enabled."""
    from app.middleware.failure_injection import FailureInjectionMiddleware

    monkeypatch.setenv("FAILURE_INJECTION_ENABLED", "true")
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_settings_cache()

    try:
        from app.main import create_app

        app = create_app()
        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, "cls")]
        assert FailureInjectionMiddleware in middleware_classes
    finally:
        _clear_settings_cache()


@allure.story("Middleware Registration")
@allure.severity(allure.severity_level.NORMAL)
def test_delay_injection_middleware_registered_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DelayInjectionMiddleware is added to the stack when the setting is enabled."""
    from app.middleware.delay_injection import DelayInjectionMiddleware

    monkeypatch.setenv("DELAY_INJECTION_ENABLED", "true")
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_settings_cache()

    try:
        from app.main import create_app

        app = create_app()
        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, "cls")]
        assert DelayInjectionMiddleware in middleware_classes
    finally:
        _clear_settings_cache()


@allure.story("Middleware Registration")
@allure.severity(allure.severity_level.MINOR)
def test_injection_middlewares_not_registered_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Neither injection middleware is added when both settings are disabled (default)."""
    from app.middleware.delay_injection import DelayInjectionMiddleware
    from app.middleware.failure_injection import FailureInjectionMiddleware

    monkeypatch.setenv("FAILURE_INJECTION_ENABLED", "false")
    monkeypatch.setenv("DELAY_INJECTION_ENABLED", "false")
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_settings_cache()

    try:
        from app.main import create_app

        app = create_app()
        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, "cls")]
        assert FailureInjectionMiddleware not in middleware_classes
        assert DelayInjectionMiddleware not in middleware_classes
    finally:
        _clear_settings_cache()


# ---------------------------------------------------------------------------
# Lifespan — startup logging paths
# ---------------------------------------------------------------------------


@allure.story("Lifespan")
@allure.severity(allure.severity_level.NORMAL)
def test_lifespan_starts_without_error_when_bypass_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """App lifespan starts cleanly when RATE_LIMIT_BYPASS_KEY is set."""
    monkeypatch.setenv("RATE_LIMIT_BYPASS_KEY", "test-bypass-secret")
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_settings_cache()

    try:
        from app.main import create_app

        with TestClient(create_app(), raise_server_exceptions=True) as client:
            response = client.get("/health")
        assert response.status_code == 200
    finally:
        _clear_settings_cache()


@allure.story("Lifespan")
@allure.severity(allure.severity_level.NORMAL)
def test_lifespan_starts_without_error_when_bypass_key_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """App lifespan starts cleanly when RATE_LIMIT_BYPASS_KEY is empty (disabled)."""
    # The default value in Settings is "MELON"; set explicitly to "" to exercise
    # the bypass-disabled log path in the lifespan startup block.
    monkeypatch.setenv("RATE_LIMIT_BYPASS_KEY", "")
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_settings_cache()

    try:
        from app.main import create_app

        with TestClient(create_app(), raise_server_exceptions=True) as client:
            response = client.get("/health")
        assert response.status_code == 200
    finally:
        _clear_settings_cache()
