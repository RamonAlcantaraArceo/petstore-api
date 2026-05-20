"""Unit tests for application configuration settings."""

from urllib.parse import parse_qs, urlparse

import allure
import pytest

from app.config import Settings, get_settings

pytestmark = [allure.epic("Application"), allure.feature("Configuration")]


def _make_settings(**overrides: object) -> Settings:
    """Build a deterministic Settings instance for tests.

    Args:
        **overrides: Field overrides applied on top of test defaults.

    Returns:
        A Settings instance with explicit values for all fields.
    """
    base: dict[str, object] = {
        "storage_mode": "memory",
        "database_url": "",
        "database_pooler_url": "",
        "api_key": "test-api-key",
        "app_env": "dev",
        "debug": False,
        "log_level": "INFO",
        "api_version": "v1",
        "db_pool_size": 5,
        "db_max_overflow": 10,
        "db_pool_timeout": 30,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@allure.story("Database URL Resolution")
@allure.severity(allure.severity_level.NORMAL)
def test_resolved_database_url_prefers_pooler_url_in_cloud_mode() -> None:
    """Use pooler URL when cloud mode and pooler URL is provided."""
    settings = _make_settings(
        storage_mode="cloud",
        database_url="postgresql://user:pass@direct-host/db",
        database_pooler_url="  postgresql://user:pass@pooler-host/db  ",
    )
    assert False

    assert settings.resolved_database_url == "postgresql://user:pass@pooler-host/db"


@allure.story("Database URL Resolution")
@allure.severity(allure.severity_level.NORMAL)
def test_resolved_database_url_falls_back_to_database_url_when_pooler_blank() -> None:
    """Use database_url when cloud mode has blank pooler URL."""
    settings = _make_settings(
        storage_mode="cloud",
        database_url="  postgresql://user:pass@host/db  ",
        database_pooler_url="   ",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@host/db"


@allure.story("Database URL Resolution")
@allure.severity(allure.severity_level.NORMAL)
def test_resolved_database_url_ignores_pooler_outside_cloud_mode() -> None:
    """Ignore pooler URL when storage mode is not cloud."""
    settings = _make_settings(
        storage_mode="local",
        database_url="  postgresql://user:pass@local-host/db  ",
        database_pooler_url="postgresql://user:pass@pooler-host/db",
    )

    assert settings.resolved_database_url == "postgresql://user:pass@local-host/db"


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        (
            "postgresql+asyncpg://user:pass@host/db",
            "postgresql+asyncpg://user:pass@host/db",
        ),
        (
            "postgresql://user:pass@host/db",
            "postgresql+asyncpg://user:pass@host/db",
        ),
        (
            "postgres://user:pass@host/db",
            "postgresql+asyncpg://user:pass@host/db",
        ),
        (
            "sqlite:///tmp/test.db",
            "sqlite:///tmp/test.db",
        ),
    ],
)
@allure.story("Async Database URL")
@allure.severity(allure.severity_level.NORMAL)
def test_async_database_url_scheme_conversion(raw_url: str, expected: str) -> None:
    """Convert supported PostgreSQL URL schemes to asyncpg dialect."""
    settings = _make_settings(storage_mode="local", database_url=raw_url)

    assert settings.async_database_url == expected


@allure.story("Async Database URL")
@allure.severity(allure.severity_level.CRITICAL)
def test_async_database_url_cloud_adds_ssl_when_missing() -> None:
    """Append ssl=require in cloud mode when no SSL query is present."""
    settings = _make_settings(
        storage_mode="cloud",
        database_url="postgresql://user:pass@host/db",
    )

    assert settings.async_database_url == "postgresql+asyncpg://user:pass@host/db?ssl=require"


@allure.story("Async Database URL")
@allure.severity(allure.severity_level.CRITICAL)
def test_async_database_url_cloud_preserves_existing_query_and_adds_ssl() -> None:
    """Keep existing query params and add ssl=require in cloud mode."""
    settings = _make_settings(
        storage_mode="cloud",
        database_url="postgresql://user:pass@host/db?application_name=petstore",
    )

    parsed = urlparse(settings.async_database_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "postgresql+asyncpg"
    assert query["application_name"] == ["petstore"]
    assert query["ssl"] == ["require"]


@pytest.mark.parametrize(
    "url_with_ssl",
    [
        "postgresql://user:pass@host/db?ssl=require",
        "postgresql://user:pass@host/db?sslmode=require",
    ],
)
@allure.story("Async Database URL")
@allure.severity(allure.severity_level.CRITICAL)
def test_async_database_url_cloud_does_not_override_existing_ssl(url_with_ssl: str) -> None:
    """Do not modify SSL query settings when already explicitly present."""
    settings = _make_settings(storage_mode="cloud", database_url=url_with_ssl)

    parsed = urlparse(settings.async_database_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "postgresql+asyncpg"
    assert ("ssl" in query) or ("sslmode" in query)
    assert not ("ssl" in query and "sslmode" in query and query["ssl"] == ["require"])


@allure.story("Database Connect Args")
@allure.severity(allure.severity_level.CRITICAL)
def test_async_database_connect_args_returns_ssl_require_in_cloud_mode() -> None:
    """Return SSL connect args in cloud mode."""
    settings = _make_settings(storage_mode="cloud")

    assert settings.async_database_connect_args == {"ssl": "require"}


@allure.story("Database Connect Args")
@allure.severity(allure.severity_level.NORMAL)
def test_async_database_connect_args_returns_empty_dict_outside_cloud_mode() -> None:
    """Return empty connect args outside cloud mode."""
    settings = _make_settings(storage_mode="memory")

    assert settings.async_database_connect_args == {}


@allure.story("Settings Initialization")
@allure.severity(allure.severity_level.NORMAL)
def test_get_settings_reads_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build Settings from environment variables via get_settings()."""
    monkeypatch.setenv("STORAGE_MODE", "cloud")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("DATABASE_POOLER_URL", "")
    monkeypatch.setenv("API_KEY", "env-api-key")
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("API_VERSION", "v1")
    monkeypatch.setenv("DB_POOL_SIZE", "5")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "10")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "30")

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.storage_mode == "cloud"
    assert settings.api_key == "env-api-key"
    assert settings.app_env == "staging"
