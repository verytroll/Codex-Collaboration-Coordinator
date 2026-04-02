from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.job_inputs import JobInputRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'public_authz.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_job(database_url: str, *, job_id: str, session_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                channel_key="general",
                assigned_agent_id="agt_builder",
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Public task",
                instructions="Public task",
                status="queued",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="queued",
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at=created_at,
                completed_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_agent(database_url: str, *, agent_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        AgentRepository(database_url).create(
            AgentRecord(
                id=agent_id,
                display_name=agent_id,
                role="builder",
                is_lead_default=0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )
    asyncio.run(
        AgentRuntimeRepository(database_url).create(
            AgentRuntimeRecord(
                id=f"rt_{agent_id}",
                agent_id=agent_id,
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status="offline",
                last_heartbeat_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(database_url: str, *, session_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title="Public",
                goal="Public",
                status="active",
                lead_agent_id="agt_lead",
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=created_at,
                template_key="template",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _create_app(
    tmp_path: Path,
    monkeypatch,
    *,
    app_env: str,
    access_boundary_mode: str,
    access_token: str | None = None,
) -> str:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", access_boundary_mode)
    if access_token is None:
        monkeypatch.delenv("ACCESS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("ACCESS_TOKEN", access_token)
    monkeypatch.delenv("ACTOR_ID_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ROLE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_TYPE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_LABEL_HEADER", raising=False)
    app_main.get_config.cache_clear()
    _migrate(database_url)
    return database_url


def test_public_write_authorization_and_bootstrap_identity(tmp_path, monkeypatch) -> None:
    database_url = _create_app(
        tmp_path,
        monkeypatch,
        app_env="production",
        access_boundary_mode="protected",
        access_token="service-token",
    )
    app = app_main.create_app()
    _seed_agent(database_url, agent_id="agt_lead")
    _seed_agent(database_url, agent_id="agt_builder")
    _seed_session(database_url, session_id="ses_public")
    _seed_job(database_url, job_id="job_public", session_id="ses_public")

    try:
        with TestClient(app) as client:
            allowed = client.post(
                "/api/v1/a2a/tasks",
                headers={
                    "X-Access-Token": "service-token",
                    "X-Actor-Id": "cli_01",
                    "X-Actor-Role": "integration_client",
                    "X-Actor-Type": "service",
                    "X-Actor-Label": "External client",
                },
                json={"job_id": "job_public"},
            )
            assert allowed.status_code == 201
            assert allowed.json()["task"]["job_id"] == "job_public"

            forbidden = client.post(
                "/api/v1/a2a/tasks",
                headers={
                    "X-Access-Token": "service-token",
                    "X-Actor-Id": "rev_01",
                    "X-Actor-Role": "reviewer",
                    "X-Actor-Type": "human",
                    "X-Actor-Label": "Reviewer",
                },
                json={"job_id": "job_public"},
            )
            assert forbidden.status_code == 403

            events = asyncio.run(SessionEventRepository(database_url).list_by_session("ses_public"))
            public_event = next(
                event for event in events if event.event_type == "public.task.projected"
            )
            assert public_event.actor_type == "integration_client"
            assert public_event.actor_id == "cli_01"
    finally:
        app_main.get_config.cache_clear()


def test_public_write_bootstraps_without_identity_in_trusted_mode(tmp_path, monkeypatch) -> None:
    database_url = _create_app(
        tmp_path,
        monkeypatch,
        app_env="production",
        access_boundary_mode="trusted",
        access_token=None,
    )
    app = app_main.create_app()
    _seed_agent(database_url, agent_id="agt_lead")
    _seed_agent(database_url, agent_id="agt_builder")
    _seed_session(database_url, session_id="ses_trusted")
    _seed_job(database_url, job_id="job_trusted", session_id="ses_trusted")

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/a2a/tasks", json={"job_id": "job_trusted"})
            assert response.status_code == 201
            assert response.json()["task"]["job_id"] == "job_trusted"

            events = asyncio.run(
                SessionEventRepository(database_url).list_by_session("ses_trusted")
            )
            assert any(event.event_type == "public.task.projected" for event in events)
            assert asyncio.run(JobInputRepository(database_url).list()) == []
    finally:
        app_main.get_config.cache_clear()
