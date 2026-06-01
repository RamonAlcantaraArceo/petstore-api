"""Configuration settings for the Petstore API."""

import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        storage_mode: Runtime mode - "memory" | "local" | "cloud".
        database_url: PostgreSQL connection URL (used when storage_mode != "memory").
        database_pooler_url: Optional PostgreSQL pooler URL for cloud mode.
        api_key: Required API key for authentication.
        app_env: Application environment - "dev" | "staging" | "prod".
        debug: Enable debug mode.
        log_level: Logging level.
        api_version: API version prefix.
        db_pool_size: SQLAlchemy connection pool size.
        db_max_overflow: SQLAlchemy max overflow connections.
        db_pool_timeout: SQLAlchemy pool timeout in seconds.
        seed_dataset: Optional fixture dataset name to load at startup
            (e.g. "basic", "mixed_v1", "mixed_v2"). Empty string disables seeding.
        rate_limit_requests: Maximum number of requests allowed per window per client key.
        rate_limit_window_seconds: Duration of the rate-limit window in seconds.
        rate_limit_bypass_key: Secret value for the ``X-Bypass-Key`` header that skips
            rate limiting. Empty string disables the bypass mechanism.

    Example:
        >>> settings = Settings(api_key="test-key")
        >>> assert settings.storage_mode == "memory"
    """

    storage_mode: str = "memory"
    database_url: str = ""
    database_pooler_url: str = ""
    api_key: str = "dev-api-key"
    app_env: str = "dev"
    debug: bool = False
    log_level: str = "INFO"
    api_version: str = "v1"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    seed_dataset: str = ""
    e2e_base_url: str = ""
    rate_limit_requests: int = 40
    rate_limit_window_seconds: int = 60
    rate_limit_bypass_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def async_database_url(self) -> str:
        """Return a SQLAlchemy async-compatible PostgreSQL URL.

        Accepts direct PostgreSQL URLs (for example, Supabase direct connection
        strings) and converts them to the asyncpg dialect expected by
        ``create_async_engine``.

        Returns:
            Async-compatible PostgreSQL connection URL.
        """
        raw_url = self.resolved_database_url
        if raw_url.startswith("postgresql+asyncpg://"):
            async_url = raw_url
        elif raw_url.startswith("postgresql://"):
            async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif raw_url.startswith("postgres://"):
            async_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
        else:
            async_url = raw_url
        return self._ensure_cloud_ssl_query(async_url)

    @property
    def async_database_connect_args(self) -> dict[str, str]:
        """Return async driver connect arguments based on runtime mode.

        Returns:
            Driver connect args for create_async_engine.
        """
        if self.storage_mode == "cloud":
            return {"ssl": "require"}
        return {}

    def _ensure_cloud_ssl_query(self, url: str) -> str:
        """Ensure SSL is required for cloud DB URLs when not explicitly set.

        Args:
            url: Candidate PostgreSQL URL.

        Returns:
            URL with a cloud-appropriate SSL query parameter when needed.
        """
        if self.storage_mode != "cloud" or not url:
            return url

        parsed = urlparse(url)
        query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if "ssl" in query_items or "sslmode" in query_items:
            return url

        query_items["ssl"] = "require"
        new_query = urlencode(query_items)
        return urlunparse(parsed._replace(query=new_query))

    @property
    def resolved_database_url(self) -> str:
        """Return the effective DB URL for the current runtime mode.

        In cloud mode, an explicit pooler URL is preferred when provided.

        Returns:
            Effective PostgreSQL connection URL.
        """
        if self.storage_mode == "cloud" and self.database_pooler_url.strip():
            return self.database_pooler_url.strip()
        return self.database_url.strip()

    @property
    def version(self) -> str:
        """Return the version from VERSION environment variable.

        Returns:
            Version value or "local" if not set.
        """
        return os.getenv("VERSION", "local")

    @property
    def build_date(self) -> str:
        """Return the build date from BUILD_DATE environment variable.

        Returns:
            Build date value or "N/A" if not set.
        """
        return os.getenv("BUILD_DATE", "N/A")

    @property
    def git_sha(self) -> str:
        """Return the Git commit SHA from GIT_SHA environment variable.

        Returns:
            Git commit SHA value or "N/A" if not set.
        """
        return os.getenv("GIT_SHA", "N/A")

    @property
    def details(self) -> dict[str, str]:
        """Return a dictionary of application details for health checks and metadata.

        Returns:
            A dictionary containing version, build date, and Git commit SHA.
        """
        return {
            "version": self.version,
            "build_date": self.build_date,
            "git_commit_sha": self.git_sha,
        }


def get_settings() -> Settings:
    """Return application settings singleton.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()
