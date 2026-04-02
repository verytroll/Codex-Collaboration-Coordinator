from __future__ import annotations

import pytest

from app.core.config import load_config


def test_load_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("APP_HOST", raising=False)
    monkeypatch.delenv("APP_PORT", raising=False)
    monkeypatch.delenv("APP_RELOAD", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CODEX_BRIDGE_MODE", raising=False)
    monkeypatch.delenv("REQUEST_ID_HEADER", raising=False)
    monkeypatch.delenv("ACCESS_BOUNDARY_MODE", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ID_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ROLE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_TYPE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_LABEL_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ID", raising=False)
    monkeypatch.delenv("ACTOR_ROLE", raising=False)
    monkeypatch.delenv("ACTOR_TYPE", raising=False)
    monkeypatch.delenv("ACTOR_LABEL", raising=False)
    monkeypatch.delenv("RUNTIME_RECOVERY_ENABLED", raising=False)
    monkeypatch.delenv("RUNTIME_RECOVERY_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("RUNTIME_STALE_AFTER_MINUTES", raising=False)

    config = load_config()

    assert config.app_name == "codex-collaboration-coordinator"
    assert config.app_env == "development"
    assert config.deployment_profile == "local-dev"
    assert config.app_host == "127.0.0.1"
    assert config.app_port == 8000
    assert config.app_reload is True
    assert config.log_level == "INFO"
    assert config.database_url == "sqlite:///./codex_coordinator.db"
    assert config.codex_bridge_mode == "local"
    assert config.request_id_header == "X-Request-ID"
    assert config.access_boundary_mode == "local"
    assert config.access_token == ""
    assert config.access_token_header == "X-Access-Token"
    assert config.actor_id_header == "X-Actor-Id"
    assert config.actor_role_header == "X-Actor-Role"
    assert config.actor_type_header == "X-Actor-Type"
    assert config.actor_label_header == "X-Actor-Label"
    assert config.actor_id == "local-operator"
    assert config.actor_role == "operator"
    assert config.actor_type == "human"
    assert config.actor_label == "Local operator"
    assert config.runtime_recovery_enabled is False
    assert config.runtime_recovery_interval_seconds == 15.0
    assert config.runtime_stale_after_minutes == 10


def test_load_config_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "custom-app")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "small-team")
    monkeypatch.setenv("APP_HOST", "127.0.0.1")
    monkeypatch.setenv("APP_PORT", "9000")
    monkeypatch.setenv("APP_RELOAD", "true")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("CODEX_BRIDGE_MODE", "remote")
    monkeypatch.setenv("REQUEST_ID_HEADER", "X-Trace-Id")
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", "protected")
    monkeypatch.setenv("ACCESS_TOKEN", "secret-token")
    monkeypatch.setenv("ACCESS_TOKEN_HEADER", "X-Service-Token")
    monkeypatch.setenv("RUNTIME_RECOVERY_ENABLED", "true")
    monkeypatch.setenv("RUNTIME_RECOVERY_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("RUNTIME_STALE_AFTER_MINUTES", "20")

    config = load_config()

    assert config.app_name == "custom-app"
    assert config.app_env == "production"
    assert config.deployment_profile == "small-team"
    assert config.app_host == "127.0.0.1"
    assert config.app_port == 9000
    assert config.app_reload is True
    assert config.log_level == "DEBUG"
    assert config.database_url == "sqlite:///./test.db"
    assert config.codex_bridge_mode == "remote"
    assert config.request_id_header == "X-Trace-Id"
    assert config.access_boundary_mode == "protected"
    assert config.access_token == "secret-token"
    assert config.access_token_header == "X-Service-Token"
    assert config.runtime_recovery_enabled is True
    assert config.runtime_recovery_interval_seconds == 30.0
    assert config.runtime_stale_after_minutes == 20


def test_load_config_applies_small_team_profile_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "small-team")
    monkeypatch.delenv("APP_HOST", raising=False)
    monkeypatch.delenv("APP_PORT", raising=False)
    monkeypatch.delenv("APP_RELOAD", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CODEX_BRIDGE_MODE", raising=False)
    monkeypatch.delenv("REQUEST_ID_HEADER", raising=False)
    monkeypatch.delenv("ACCESS_BOUNDARY_MODE", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ID_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ROLE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_TYPE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_LABEL_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ID", raising=False)
    monkeypatch.delenv("ACTOR_ROLE", raising=False)
    monkeypatch.delenv("ACTOR_TYPE", raising=False)
    monkeypatch.delenv("ACTOR_LABEL", raising=False)
    monkeypatch.delenv("RUNTIME_RECOVERY_ENABLED", raising=False)
    monkeypatch.delenv("RUNTIME_RECOVERY_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("RUNTIME_STALE_AFTER_MINUTES", raising=False)

    config = load_config()

    assert config.app_env == "production"
    assert config.deployment_profile == "small-team"
    assert config.app_host == "0.0.0.0"
    assert config.app_reload is False
    assert config.database_url == "sqlite:///./data/codex_coordinator.db"
    assert config.access_boundary_mode == "trusted"
    assert config.actor_role == "operator"
    assert config.runtime_recovery_enabled is False
