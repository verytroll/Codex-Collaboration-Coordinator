from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.services.demo_seed import seed_demo_data


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'operator_ui_smoke.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def test_operator_shell_smoke_contract(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "development")
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    asyncio.run(seed_demo_data(database_url))

    try:
        with TestClient(app) as client:
            page_response = client.get("/operator")
            assert page_response.status_code == 200
            assert "Operator Shell" in page_response.text
            assert 'id="summary-cards"' in page_response.text
            assert 'id="session-list"' in page_response.text
            assert 'id="selected-session"' in page_response.text
            assert 'id="dashboard-bottlenecks"' in page_response.text
            assert "/api/v1/operator/shell" in page_response.text

            bootstrap_response = client.get(
                "/api/v1/operator/shell",
                params={"session_id": "ses_demo"},
            )
            assert bootstrap_response.status_code == 200
            payload = bootstrap_response.json()

            assert payload["selected_session_id"] == "ses_demo"
            assert payload["sessions"]
            assert payload["selected_session"]["session"]["id"] == "ses_demo"
            assert payload["dashboard"]["filters"]["session_id"] == "ses_demo"

            activity_response = client.get(
                "/api/v1/operator/sessions/ses_demo/activity",
                params={"since_sequence": 0, "limit": 5},
            )
            assert activity_response.status_code == 200
            activity_payload = activity_response.json()
            assert activity_payload["session_id"] == "ses_demo"
            assert activity_payload["events"]
            assert activity_payload["signals"]["pending_approvals"] is not None
            assert activity_payload["signals"]["stuck_jobs"] is not None
    finally:
        app_main.get_config.cache_clear()
