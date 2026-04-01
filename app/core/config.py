"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_APP_NAME = "codex-collaboration-coordinator"
DEFAULT_APP_ENV = "development"
DEFAULT_APP_HOST = "0.0.0.0"
DEFAULT_APP_PORT = 8000
DEFAULT_APP_RELOAD = False
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_DATABASE_URL = "sqlite:///./codex_coordinator.db"
DEFAULT_CODEX_BRIDGE_MODE = "local"
DEFAULT_REQUEST_ID_HEADER = "X-Request-ID"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Runtime configuration loaded from environment variables."""

    app_name: str = DEFAULT_APP_NAME
    app_env: str = DEFAULT_APP_ENV
    app_host: str = DEFAULT_APP_HOST
    app_port: int = DEFAULT_APP_PORT
    app_reload: bool = DEFAULT_APP_RELOAD
    log_level: str = DEFAULT_LOG_LEVEL
    database_url: str = DEFAULT_DATABASE_URL
    codex_bridge_mode: str = DEFAULT_CODEX_BRIDGE_MODE
    request_id_header: str = DEFAULT_REQUEST_ID_HEADER


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    return AppConfig(
        app_name=os.getenv("APP_NAME", DEFAULT_APP_NAME),
        app_env=os.getenv("APP_ENV", DEFAULT_APP_ENV),
        app_host=os.getenv("APP_HOST", DEFAULT_APP_HOST),
        app_port=int(os.getenv("APP_PORT", str(DEFAULT_APP_PORT))),
        app_reload=_parse_bool(os.getenv("APP_RELOAD"), DEFAULT_APP_RELOAD),
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        codex_bridge_mode=os.getenv("CODEX_BRIDGE_MODE", DEFAULT_CODEX_BRIDGE_MODE),
        request_id_header=os.getenv("REQUEST_ID_HEADER", DEFAULT_REQUEST_ID_HEADER),
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return a cached configuration instance."""
    return load_config()
