from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'access_boundary.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _create_app(
    tmp_path: Path,
    monkeypatch,
    *,
    app_env: str,
    access_boundary_mode: str | None = None,
    access_token: str | None = None,
    access_token_header: str | None = None,
):
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", app_env)
    if access_boundary_mode is None:
        monkeypatch.delenv("ACCESS_BOUNDARY_MODE", raising=False)
    else:
        monkeypatch.setenv("ACCESS_BOUNDARY_MODE", access_boundary_mode)
    if access_token is None:
        monkeypatch.delenv("ACCESS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("ACCESS_TOKEN", access_token)
    if access_token_header is None:
        monkeypatch.delenv("ACCESS_TOKEN_HEADER", raising=False)
    else:
        monkeypatch.setenv("ACCESS_TOKEN_HEADER", access_token_header)

    app_main.get_config.cache_clear()
    _migrate(database_url)
    return app_main.create_app()


def _assert_access_error(response, *, code: str) -> None:
    assert response.status_code in {401, 403}
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["request_id"]


def test_operator_and_public_surfaces_allow_local_mode_without_token(tmp_path, monkeypatch) -> None:
    app = _create_app(tmp_path, monkeypatch, app_env="development")

    try:
        with TestClient(app) as client:
            operator_response = client.get("/api/v1/operator/dashboard")
            assert operator_response.status_code == 200
            assert operator_response.json()["filters"] == {
                "session_id": None,
                "template_key": None,
                "phase_key": None,
                "runtime_pool_key": None,
            }

            shell_response = client.get("/operator")
            assert shell_response.status_code == 200
            assert "Operator Shell" in shell_response.text

            public_response = client.get("/.well-known/agent-card.json")
            assert public_response.status_code == 200
            assert public_response.json()["name"] == "Codex Collaboration Coordinator"
    finally:
        app_main.get_config.cache_clear()


def test_operator_and_public_surfaces_allow_trusted_local_clients_without_token(
    tmp_path,
    monkeypatch,
) -> None:
    app = _create_app(tmp_path, monkeypatch, app_env="production", access_boundary_mode="trusted")

    try:
        with TestClient(app) as client:
            operator_response = client.get("/api/v1/operator/dashboard")
            assert operator_response.status_code == 200

            shell_response = client.get("/operator")
            assert shell_response.status_code == 200

            public_response = client.get("/.well-known/agent-card.json")
            assert public_response.status_code == 200
    finally:
        app_main.get_config.cache_clear()


def test_operator_and_public_surfaces_require_service_token_in_protected_mode(
    tmp_path,
    monkeypatch,
) -> None:
    app = _create_app(
        tmp_path,
        monkeypatch,
        app_env="production",
        access_boundary_mode="protected",
        access_token="service-token",
        access_token_header="X-Access-Token",
    )

    try:
        with TestClient(app) as client:
            unauthorized_response = client.get("/api/v1/operator/dashboard")
            _assert_access_error(unauthorized_response, code="access_unauthorized")

            unauthorized_shell_response = client.get("/operator")
            _assert_access_error(unauthorized_shell_response, code="access_unauthorized")

            forbidden_response = client.get(
                "/api/v1/operator/dashboard",
                headers={"X-Access-Token": "wrong-token"},
            )
            _assert_access_error(forbidden_response, code="access_forbidden")

            forbidden_shell_response = client.get(
                "/operator",
                headers={"X-Access-Token": "wrong-token"},
            )
            _assert_access_error(forbidden_shell_response, code="access_forbidden")

            allowed_operator_response = client.get(
                "/api/v1/operator/dashboard",
                headers={"X-Access-Token": "service-token"},
            )
            assert allowed_operator_response.status_code == 200

            allowed_shell_response = client.get(
                "/operator",
                headers={"X-Access-Token": "service-token"},
            )
            assert allowed_shell_response.status_code == 200

            unauthorized_public_response = client.get("/.well-known/agent-card.json")
            _assert_access_error(unauthorized_public_response, code="access_unauthorized")

            allowed_public_response = client.get(
                "/.well-known/agent-card.json",
                headers={"X-Access-Token": "service-token"},
            )
            assert allowed_public_response.status_code == 200
    finally:
        app_main.get_config.cache_clear()
