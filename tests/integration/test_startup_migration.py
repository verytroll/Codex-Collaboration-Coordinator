from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'startup.db').as_posix()}"


def test_app_startup_migrates_fresh_database(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    app_main.get_config.cache_clear()

    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Starter",
                    "role": "planner",
                    "is_lead": True,
                    "runtime_kind": "codex",
                },
            )
            assert response.status_code == 201
            assert response.json()["agent"]["id"].startswith("agt_")
    finally:
        app_main.get_config.cache_clear()
