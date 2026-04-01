from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.api.dependencies import get_deployment_readiness_service
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'deployment.db').as_posix()}"


def test_deployment_readiness_returns_ready_payload(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "production")
    app_main.get_config.cache_clear()
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/readinessz")

            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "ok"
            assert payload["app"]["env"] == "production"
            assert payload["checks"]["db"]["status"] == "ok"
            assert payload["checks"]["migrations"]["status"] == "ok"
            assert "migration(s) applied" in payload["checks"]["migrations"]["detail"]
    finally:
        app_main.get_config.cache_clear()


def test_deployment_readiness_returns_503_when_dependency_is_unavailable(
    tmp_path,
    monkeypatch,
) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    class FakeReadinessService:
        async def get_readiness(self) -> dict[str, object]:
            return {
                "status": "unavailable",
                "checks": {
                    "db": {
                        "status": "ok",
                        "detail": "SQLite reachable.",
                    },
                    "migrations": {
                        "status": "unavailable",
                        "detail": "Pending migration(s): 019_future.sql",
                    },
                },
            }

    app.dependency_overrides[get_deployment_readiness_service] = lambda: FakeReadinessService()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/readinessz")

            assert response.status_code == 503
            payload = response.json()
            assert payload["status"] == "unavailable"
            assert payload["checks"]["migrations"]["status"] == "unavailable"
    finally:
        app.dependency_overrides.clear()
        app_main.get_config.cache_clear()
