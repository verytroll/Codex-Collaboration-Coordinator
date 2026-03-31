from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'api.db').as_posix()}"


@pytest.fixture
def api_app(tmp_path, monkeypatch):
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    app_main.get_config.cache_clear()
    _migrate(database_url)
    app = app_main.create_app()
    yield app
    app_main.get_config.cache_clear()


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def test_session_api_crud(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            agent_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Lead Planner",
                    "role": "planner",
                    "is_lead": True,
                    "runtime_kind": "codex",
                    "runtime_config": {
                        "workspace_path": "/workspace/project",
                        "sandbox_mode": "workspace-write",
                    },
                },
            )
            assert agent_response.status_code == 201
            agent_id = agent_response.json()["agent"]["id"]

            create_response = client.post(
                "/api/v1/sessions",
                json={
                    "title": "Fix login flow",
                    "goal": "Coordinate planner and builder",
                    "lead_agent_id": agent_id,
                },
            )
            assert create_response.status_code == 201
            session_body = create_response.json()["session"]
            session_id = session_body["id"]
            assert session_body["status"] == "active"
            assert session_body["lead_agent_id"] == agent_id
            assert session_body["active_phase_id"] is not None

            channels_response = client.get(f"/api/v1/sessions/{session_id}/channels")
            assert channels_response.status_code == 200
            channel_keys = [
                channel["channel_key"] for channel in channels_response.json()["channels"]
            ]
            assert channel_keys == ["general", "planning", "review", "debug"]

            phases_response = client.get(f"/api/v1/sessions/{session_id}/phases")
            assert phases_response.status_code == 200
            phase_keys = [phase["phase_key"] for phase in phases_response.json()["phases"]]
            assert phase_keys == [
                "planning",
                "implementation",
                "review",
                "revise",
                "finalize",
            ]
            assert phases_response.json()["phases"][0]["is_active"] is True

            list_response = client.get("/api/v1/sessions")
            assert list_response.status_code == 200
            assert list_response.json()["sessions"][0]["id"] == session_id

            get_response = client.get(f"/api/v1/sessions/{session_id}")
            assert get_response.status_code == 200
            assert get_response.json()["session"]["title"] == "Fix login flow"

            patch_response = client.patch(
                f"/api/v1/sessions/{session_id}",
                json={
                    "title": "Fix login flow v2",
                    "goal": "Updated coordination goal",
                    "status": "paused",
                },
            )
            assert patch_response.status_code == 200
            patched_session = patch_response.json()["session"]
            assert patched_session["title"] == "Fix login flow v2"
            assert patched_session["goal"] == "Updated coordination goal"
            assert patched_session["status"] == "paused"
    finally:
        app_main.get_config.cache_clear()


def test_agent_api_crud(api_app) -> None:
    with TestClient(api_app) as client:
        create_response = client.post(
            "/api/v1/agents",
            json={
                "display_name": "Builder",
                "role": "builder",
                "is_lead": False,
                "runtime_kind": "codex",
                "runtime_config": {
                    "workspace_path": "/workspace/project",
                    "sandbox_mode": "workspace-write",
                },
            },
        )
        assert create_response.status_code == 201
        agent_body = create_response.json()["agent"]
        agent_id = agent_body["id"]
        assert agent_body["presence"] == "unknown"
        assert agent_body["runtime_id"] is not None
        assert agent_body["capabilities"]["can_code"] is True

        list_response = client.get("/api/v1/agents")
        assert list_response.status_code == 200
        assert list_response.json()["agents"][0]["id"] == agent_id

        get_response = client.get(f"/api/v1/agents/{agent_id}")
        assert get_response.status_code == 200
        assert get_response.json()["agent"]["display_name"] == "Builder"

        patch_response = client.patch(
            f"/api/v1/agents/{agent_id}",
            json={
                "display_name": "Builder Pro",
                "role": "reviewer",
                "is_lead": True,
            },
        )
        assert patch_response.status_code == 200
        patched_agent = patch_response.json()["agent"]
        assert patched_agent["display_name"] == "Builder Pro"
        assert patched_agent["role"] == "reviewer"
        assert patched_agent["is_lead"] is True
        assert patched_agent["capabilities"]["can_review"] is True
