from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'a2a.db').as_posix()}"


def test_agent_card_placeholder_and_healthz(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    app_main.get_config.cache_clear()
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            health_response = client.get("/api/v1/healthz")
            assert health_response.status_code == 200
            assert health_response.json() == {"status": "ok"}

            agent_card_response = client.get("/.well-known/agent-card.json")
            assert agent_card_response.status_code == 200
            body = agent_card_response.json()
            assert body["name"] == "Codex Collaboration Coordinator"
            assert body["capabilities"] == {
                "streaming": True,
                "push_notifications": True,
                "task_delegation": True,
                "artifacts": True,
            }
            assert [skill["id"] for skill in body["skills"]] == [
                "collaboration",
                "codex-execution",
            ]
    finally:
        app_main.get_config.cache_clear()
