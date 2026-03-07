"""Configuration settings for the Petstore API."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        storage_mode: Runtime mode - "memory" | "local" | "cloud".
        database_url: PostgreSQL connection URL (used when storage_mode != "memory").
        api_key: Required API key for authentication.
        app_env: Application environment - "dev" | "staging" | "prod".
        debug: Enable debug mode.
        log_level: Logging level.
        api_version: API version prefix.
        db_pool_size: SQLAlchemy connection pool size.
        db_max_overflow: SQLAlchemy max overflow connections.
        db_pool_timeout: SQLAlchemy pool timeout in seconds.

    Example:
        >>> settings = Settings(api_key="test-key")
        >>> assert settings.storage_mode == "memory"
    """

    storage_mode: str = "memory"
    database_url: str = ""
    api_key: str = "dev-api-key"
    app_env: str = "dev"
    debug: bool = False
    log_level: str = "INFO"
    api_version: str = "v1"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Return application settings singleton.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()
