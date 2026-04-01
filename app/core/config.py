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
DEFAULT_ACCESS_BOUNDARY_MODE_LOCAL = "local"
DEFAULT_ACCESS_BOUNDARY_MODE_TRUSTED = "trusted"
DEFAULT_ACCESS_BOUNDARY_MODE_PROTECTED = "protected"
DEFAULT_ACCESS_TOKEN_HEADER = "X-Access-Token"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_access_boundary_mode(app_env: str) -> str:
    if app_env.strip().lower() in {"development", "testing"}:
        return DEFAULT_ACCESS_BOUNDARY_MODE_LOCAL
    return DEFAULT_ACCESS_BOUNDARY_MODE_TRUSTED


def _normalize_access_boundary_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {
        DEFAULT_ACCESS_BOUNDARY_MODE_LOCAL,
        DEFAULT_ACCESS_BOUNDARY_MODE_TRUSTED,
        DEFAULT_ACCESS_BOUNDARY_MODE_PROTECTED,
    }:
        return normalized
    return DEFAULT_ACCESS_BOUNDARY_MODE_TRUSTED


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
    access_boundary_mode: str = DEFAULT_ACCESS_BOUNDARY_MODE_LOCAL
    access_token: str = ""
    access_token_header: str = DEFAULT_ACCESS_TOKEN_HEADER


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    app_env = os.getenv("APP_ENV", DEFAULT_APP_ENV)
    access_boundary_mode_value = os.getenv("ACCESS_BOUNDARY_MODE")
    access_token_header_value = os.getenv("ACCESS_TOKEN_HEADER")
    if access_boundary_mode_value is None or not access_boundary_mode_value.strip():
        access_boundary_mode = _default_access_boundary_mode(app_env)
    else:
        access_boundary_mode = _normalize_access_boundary_mode(access_boundary_mode_value)
    if access_token_header_value is None or not access_token_header_value.strip():
        access_token_header = DEFAULT_ACCESS_TOKEN_HEADER
    else:
        access_token_header = access_token_header_value.strip()
    return AppConfig(
        app_name=os.getenv("APP_NAME", DEFAULT_APP_NAME),
        app_env=app_env,
        app_host=os.getenv("APP_HOST", DEFAULT_APP_HOST),
        app_port=int(os.getenv("APP_PORT", str(DEFAULT_APP_PORT))),
        app_reload=_parse_bool(os.getenv("APP_RELOAD"), DEFAULT_APP_RELOAD),
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        codex_bridge_mode=os.getenv("CODEX_BRIDGE_MODE", DEFAULT_CODEX_BRIDGE_MODE),
        request_id_header=os.getenv("REQUEST_ID_HEADER", DEFAULT_REQUEST_ID_HEADER),
        access_boundary_mode=access_boundary_mode,
        access_token=os.getenv("ACCESS_TOKEN", "").strip(),
        access_token_header=access_token_header,
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return a cached configuration instance."""
    return load_config()
