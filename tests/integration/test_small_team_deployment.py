from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.services.demo_seed import seed_demo_data


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'small_team.db').as_posix()}"


def test_small_team_profile_boots_readily_and_exposes_profile(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "small-team")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ACCESS_BOUNDARY_MODE", raising=False)
    app_main.get_config.cache_clear()
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))
    asyncio.run(seed_demo_data(database_url))
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            readiness_response = client.get("/api/v1/readinessz")
            assert readiness_response.status_code == 200
            readiness_payload = readiness_response.json()
            assert readiness_payload["app"]["deployment_profile"] == "small-team"
            assert readiness_payload["app"]["env"] == "production"
            assert readiness_payload["checks"]["db"]["status"] == "ok"

            status_response = client.get("/api/v1/system/status")
            assert status_response.status_code == 200
            status_payload = status_response.json()
            assert status_payload["app"]["deployment_profile"] == "small-team"
            assert status_payload["app"]["env"] == "production"

            shell_response = client.get("/operator", params={"session_id": "ses_demo"})
            assert shell_response.status_code == 200
            assert "Operator Shell" in shell_response.text

            bootstrap_response = client.get(
                "/api/v1/operator/shell",
                params={"session_id": "ses_demo"},
            )
            assert bootstrap_response.status_code == 200
            bootstrap_payload = bootstrap_response.json()
            assert bootstrap_payload["selected_session_id"] == "ses_demo"
            assert bootstrap_payload["selected_session"]["session"]["id"] == "ses_demo"
    finally:
        app_main.get_config.cache_clear()
