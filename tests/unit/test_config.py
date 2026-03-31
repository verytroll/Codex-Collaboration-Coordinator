from __future__ import annotations

import pytest

from app.core.config import load_config


def test_load_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CODEX_BRIDGE_MODE", raising=False)
    monkeypatch.delenv("REQUEST_ID_HEADER", raising=False)

    config = load_config()

    assert config.app_name == "codex-collaboration-coordinator"
    assert config.app_env == "development"
    assert config.log_level == "INFO"
    assert config.database_url == "sqlite:///./codex_coordinator.db"
    assert config.codex_bridge_mode == "local"
    assert config.request_id_header == "X-Request-ID"


def test_load_config_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "custom-app")
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("CODEX_BRIDGE_MODE", "remote")
    monkeypatch.setenv("REQUEST_ID_HEADER", "X-Trace-Id")

    config = load_config()

    assert config.app_name == "custom-app"
    assert config.app_env == "testing"
    assert config.log_level == "DEBUG"
    assert config.database_url == "sqlite:///./test.db"
    assert config.codex_bridge_mode == "remote"
    assert config.request_id_header == "X-Trace-Id"
