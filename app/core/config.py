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
DEFAULT_ACTOR_ID_HEADER = "X-Actor-Id"
DEFAULT_ACTOR_ROLE_HEADER = "X-Actor-Role"
DEFAULT_ACTOR_TYPE_HEADER = "X-Actor-Type"
DEFAULT_ACTOR_LABEL_HEADER = "X-Actor-Label"
DEFAULT_ACTOR_ID = "local-operator"
DEFAULT_ACTOR_ROLE = "operator"
DEFAULT_ACTOR_TYPE = "human"
DEFAULT_ACTOR_LABEL = "Local operator"
DEFAULT_RUNTIME_RECOVERY_ENABLED = False
DEFAULT_RUNTIME_RECOVERY_INTERVAL_SECONDS = 15.0
DEFAULT_RUNTIME_STALE_AFTER_MINUTES = 10
DEFAULT_DEPLOYMENT_PROFILE_LOCAL_DEV = "local-dev"
DEFAULT_DEPLOYMENT_PROFILE_TRUSTED_DEMO = "trusted-demo"
DEFAULT_DEPLOYMENT_PROFILE_SMALL_TEAM = "small-team"
VALID_DEPLOYMENT_PROFILES = {
    DEFAULT_DEPLOYMENT_PROFILE_LOCAL_DEV,
    DEFAULT_DEPLOYMENT_PROFILE_TRUSTED_DEMO,
    DEFAULT_DEPLOYMENT_PROFILE_SMALL_TEAM,
}


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_access_boundary_mode(app_env: str) -> str:
    if app_env.strip().lower() in {"development", "testing"}:
        return DEFAULT_ACCESS_BOUNDARY_MODE_LOCAL
    return DEFAULT_ACCESS_BOUNDARY_MODE_TRUSTED


def _default_deployment_profile(app_env: str) -> str:
    if app_env.strip().lower() in {"development", "testing"}:
        return DEFAULT_DEPLOYMENT_PROFILE_LOCAL_DEV
    return DEFAULT_DEPLOYMENT_PROFILE_TRUSTED_DEMO


def _normalize_deployment_profile(value: str, app_env: str) -> str:
    normalized = value.strip().lower()
    if normalized in VALID_DEPLOYMENT_PROFILES:
        return normalized
    return _default_deployment_profile(app_env)


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
class DeploymentProfileDefaults:
    """Fallback values associated with a deployment profile."""

    app_env: str
    app_host: str
    app_reload: bool
    database_url: str
    access_boundary_mode: str
    runtime_recovery_enabled: bool
    runtime_recovery_interval_seconds: float
    runtime_stale_after_minutes: int


_DEPLOYMENT_PROFILE_DEFAULTS: dict[str, DeploymentProfileDefaults] = {
    DEFAULT_DEPLOYMENT_PROFILE_LOCAL_DEV: DeploymentProfileDefaults(
        app_env=DEFAULT_APP_ENV,
        app_host="127.0.0.1",
        app_reload=True,
        database_url="sqlite:///./codex_coordinator.db",
        access_boundary_mode=DEFAULT_ACCESS_BOUNDARY_MODE_LOCAL,
        runtime_recovery_enabled=False,
        runtime_recovery_interval_seconds=DEFAULT_RUNTIME_RECOVERY_INTERVAL_SECONDS,
        runtime_stale_after_minutes=DEFAULT_RUNTIME_STALE_AFTER_MINUTES,
    ),
    DEFAULT_DEPLOYMENT_PROFILE_TRUSTED_DEMO: DeploymentProfileDefaults(
        app_env="production",
        app_host="127.0.0.1",
        app_reload=False,
        database_url="sqlite:///./codex_coordinator.db",
        access_boundary_mode=DEFAULT_ACCESS_BOUNDARY_MODE_TRUSTED,
        runtime_recovery_enabled=False,
        runtime_recovery_interval_seconds=DEFAULT_RUNTIME_RECOVERY_INTERVAL_SECONDS,
        runtime_stale_after_minutes=DEFAULT_RUNTIME_STALE_AFTER_MINUTES,
    ),
    DEFAULT_DEPLOYMENT_PROFILE_SMALL_TEAM: DeploymentProfileDefaults(
        app_env="production",
        app_host="0.0.0.0",
        app_reload=False,
        database_url="sqlite:///./data/codex_coordinator.db",
        access_boundary_mode=DEFAULT_ACCESS_BOUNDARY_MODE_TRUSTED,
        runtime_recovery_enabled=True,
        runtime_recovery_interval_seconds=DEFAULT_RUNTIME_RECOVERY_INTERVAL_SECONDS,
        runtime_stale_after_minutes=DEFAULT_RUNTIME_STALE_AFTER_MINUTES,
    ),
}


def get_deployment_profile_defaults(deployment_profile: str) -> DeploymentProfileDefaults:
    """Return canonical defaults for a deployment profile."""
    return _DEPLOYMENT_PROFILE_DEFAULTS.get(
        deployment_profile,
        _DEPLOYMENT_PROFILE_DEFAULTS[DEFAULT_DEPLOYMENT_PROFILE_TRUSTED_DEMO],
    )


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Runtime configuration loaded from environment variables."""

    app_name: str = DEFAULT_APP_NAME
    app_env: str = DEFAULT_APP_ENV
    deployment_profile: str = DEFAULT_DEPLOYMENT_PROFILE_LOCAL_DEV
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
    actor_id_header: str = DEFAULT_ACTOR_ID_HEADER
    actor_role_header: str = DEFAULT_ACTOR_ROLE_HEADER
    actor_type_header: str = DEFAULT_ACTOR_TYPE_HEADER
    actor_label_header: str = DEFAULT_ACTOR_LABEL_HEADER
    actor_id: str = DEFAULT_ACTOR_ID
    actor_role: str = DEFAULT_ACTOR_ROLE
    actor_type: str = DEFAULT_ACTOR_TYPE
    actor_label: str = DEFAULT_ACTOR_LABEL
    runtime_recovery_enabled: bool = DEFAULT_RUNTIME_RECOVERY_ENABLED
    runtime_recovery_interval_seconds: float = DEFAULT_RUNTIME_RECOVERY_INTERVAL_SECONDS
    runtime_stale_after_minutes: int = DEFAULT_RUNTIME_STALE_AFTER_MINUTES


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    app_env_value = os.getenv("APP_ENV")
    deployment_profile_value = os.getenv("DEPLOYMENT_PROFILE")
    if deployment_profile_value is None or not deployment_profile_value.strip():
        deployment_profile = _default_deployment_profile(app_env_value or DEFAULT_APP_ENV)
    else:
        deployment_profile = _normalize_deployment_profile(
            deployment_profile_value,
            app_env_value or DEFAULT_APP_ENV,
        )
    profile_defaults = get_deployment_profile_defaults(deployment_profile)
    access_boundary_mode_value = os.getenv("ACCESS_BOUNDARY_MODE")
    access_token_header_value = os.getenv("ACCESS_TOKEN_HEADER")
    actor_id_header_value = os.getenv("ACTOR_ID_HEADER")
    actor_role_header_value = os.getenv("ACTOR_ROLE_HEADER")
    actor_type_header_value = os.getenv("ACTOR_TYPE_HEADER")
    actor_label_header_value = os.getenv("ACTOR_LABEL_HEADER")
    runtime_recovery_enabled_value = os.getenv("RUNTIME_RECOVERY_ENABLED")
    runtime_recovery_interval_seconds_value = os.getenv("RUNTIME_RECOVERY_INTERVAL_SECONDS")
    runtime_stale_after_minutes_value = os.getenv("RUNTIME_STALE_AFTER_MINUTES")
    if access_boundary_mode_value is None or not access_boundary_mode_value.strip():
        access_boundary_mode = profile_defaults.access_boundary_mode
    else:
        access_boundary_mode = _normalize_access_boundary_mode(access_boundary_mode_value)
    if access_token_header_value is None or not access_token_header_value.strip():
        access_token_header = DEFAULT_ACCESS_TOKEN_HEADER
    else:
        access_token_header = access_token_header_value.strip()
    if actor_id_header_value is None or not actor_id_header_value.strip():
        actor_id_header = DEFAULT_ACTOR_ID_HEADER
    else:
        actor_id_header = actor_id_header_value.strip()
    if actor_role_header_value is None or not actor_role_header_value.strip():
        actor_role_header = DEFAULT_ACTOR_ROLE_HEADER
    else:
        actor_role_header = actor_role_header_value.strip()
    if actor_type_header_value is None or not actor_type_header_value.strip():
        actor_type_header = DEFAULT_ACTOR_TYPE_HEADER
    else:
        actor_type_header = actor_type_header_value.strip()
    if actor_label_header_value is None or not actor_label_header_value.strip():
        actor_label_header = DEFAULT_ACTOR_LABEL_HEADER
    else:
        actor_label_header = actor_label_header_value.strip()
    if runtime_recovery_enabled_value is None or not runtime_recovery_enabled_value.strip():
        runtime_recovery_enabled = profile_defaults.runtime_recovery_enabled
    else:
        runtime_recovery_enabled = _parse_bool(
            runtime_recovery_enabled_value,
            DEFAULT_RUNTIME_RECOVERY_ENABLED,
        )
    if (
        runtime_recovery_interval_seconds_value is None
        or not runtime_recovery_interval_seconds_value.strip()
    ):
        runtime_recovery_interval_seconds = profile_defaults.runtime_recovery_interval_seconds
    else:
        runtime_recovery_interval_seconds = float(runtime_recovery_interval_seconds_value)
    if runtime_stale_after_minutes_value is None or not runtime_stale_after_minutes_value.strip():
        runtime_stale_after_minutes = profile_defaults.runtime_stale_after_minutes
    else:
        runtime_stale_after_minutes = int(runtime_stale_after_minutes_value)
    return AppConfig(
        app_name=os.getenv("APP_NAME", DEFAULT_APP_NAME),
        app_env=app_env_value or profile_defaults.app_env,
        deployment_profile=deployment_profile,
        app_host=os.getenv("APP_HOST", profile_defaults.app_host),
        app_port=int(os.getenv("APP_PORT", str(DEFAULT_APP_PORT))),
        app_reload=_parse_bool(os.getenv("APP_RELOAD"), profile_defaults.app_reload),
        log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        database_url=os.getenv("DATABASE_URL", profile_defaults.database_url),
        codex_bridge_mode=os.getenv("CODEX_BRIDGE_MODE", DEFAULT_CODEX_BRIDGE_MODE),
        request_id_header=os.getenv("REQUEST_ID_HEADER", DEFAULT_REQUEST_ID_HEADER),
        access_boundary_mode=access_boundary_mode,
        access_token=os.getenv("ACCESS_TOKEN", "").strip(),
        access_token_header=access_token_header,
        actor_id_header=actor_id_header,
        actor_role_header=actor_role_header,
        actor_type_header=actor_type_header,
        actor_label_header=actor_label_header,
        actor_id=os.getenv("ACTOR_ID", DEFAULT_ACTOR_ID).strip() or DEFAULT_ACTOR_ID,
        actor_role=os.getenv("ACTOR_ROLE", DEFAULT_ACTOR_ROLE).strip() or DEFAULT_ACTOR_ROLE,
        actor_type=os.getenv("ACTOR_TYPE", DEFAULT_ACTOR_TYPE).strip() or DEFAULT_ACTOR_TYPE,
        actor_label=os.getenv("ACTOR_LABEL", DEFAULT_ACTOR_LABEL).strip() or DEFAULT_ACTOR_LABEL,
        runtime_recovery_enabled=runtime_recovery_enabled,
        runtime_recovery_interval_seconds=runtime_recovery_interval_seconds,
        runtime_stale_after_minutes=runtime_stale_after_minutes,
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return a cached configuration instance."""
    return load_config()
