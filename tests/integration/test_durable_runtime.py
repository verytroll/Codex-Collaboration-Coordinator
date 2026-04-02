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
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.presence import PresenceHeartbeatRecord, PresenceRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'durable_runtime.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent_and_session(
    database_url: str,
    *,
    session_id: str,
    agent_id: str,
    runtime_status: str,
) -> None:
    now = "2026-04-01T00:00:00Z"
    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    session_repository = SessionRepository(database_url)
    asyncio.run(
        agent_repository.create(
            AgentRecord(
                id=agent_id,
                display_name="Durable Operator",
                role="planner",
                is_lead_default=1,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
    )
    asyncio.run(
        runtime_repository.create(
            AgentRuntimeRecord(
                id=f"rt_{agent_id}",
                agent_id=agent_id,
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status=runtime_status,
                last_heartbeat_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    )
    asyncio.run(
        session_repository.create(
            SessionRecord(
                id=session_id,
                title="Durable runtime",
                goal="Exercise recovery replay",
                status="active",
                lead_agent_id=agent_id,
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    )


def test_durable_runtime_startup_replays_queued_jobs(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "small-team")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CODEX_BRIDGE_MODE", "mock")
    monkeypatch.setenv("RUNTIME_RECOVERY_ENABLED", "true")
    monkeypatch.setenv("RUNTIME_RECOVERY_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("RUNTIME_STALE_AFTER_MINUTES", "10")
    app_main.get_config.cache_clear()
    _migrate(database_url)
    _seed_agent_and_session(
        database_url,
        session_id="ses_durable",
        agent_id="agt_durable",
        runtime_status="online",
    )
    job_repository = JobRepository(database_url)
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        job_repository.create(
            JobRecord(
                id="job_durable",
                session_id="ses_durable",
                assigned_agent_id="agt_durable",
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Durable replay",
                instructions="Replay this queued job on startup.",
                status="queued",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status=None,
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at=None,
                completed_at=None,
                created_at=now,
                updated_at=now,
                channel_key="general",
            )
        )
    )

    app = app_main.create_app()
    try:
        with TestClient(app):
            stored_job = asyncio.run(job_repository.get("job_durable"))
            assert stored_job is not None
            assert stored_job.status == "running"
            assert stored_job.codex_thread_id is not None
            assert stored_job.codex_thread_id.startswith("thr_mock_")
            supervisor = app.state.durable_runtime_supervisor
            assert supervisor.last_result is not None
            assert supervisor.last_result.recovery.replayed_jobs == 1
            assert supervisor.last_result.completed_at.endswith("Z")
    finally:
        app_main.get_config.cache_clear()


def test_durable_runtime_startup_marks_stale_runtime_offline(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "small-team")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CODEX_BRIDGE_MODE", "mock")
    monkeypatch.setenv("RUNTIME_RECOVERY_ENABLED", "true")
    monkeypatch.setenv("RUNTIME_RECOVERY_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("RUNTIME_STALE_AFTER_MINUTES", "10")
    app_main.get_config.cache_clear()
    _migrate(database_url)
    _seed_agent_and_session(
        database_url,
        session_id="ses_stale",
        agent_id="agt_stale",
        runtime_status="online",
    )
    presence_repository = PresenceRepository(database_url)
    asyncio.run(
        presence_repository.create(
            PresenceHeartbeatRecord(
                id="phb_stale",
                agent_id="agt_stale",
                runtime_id="rt_agt_stale",
                presence="online",
                heartbeat_at="2026-01-01T00:00:00Z",
                details_json=None,
                created_at="2026-01-01T00:00:00Z",
            )
        )
    )

    app = app_main.create_app()
    try:
        with TestClient(app):
            runtime_repository = AgentRuntimeRepository(database_url)
            stored_runtime = asyncio.run(runtime_repository.get("rt_agt_stale"))
            assert stored_runtime is not None
            assert stored_runtime.runtime_status == "offline"
            supervisor = app.state.durable_runtime_supervisor
            assert supervisor.last_result is not None
            assert supervisor.last_result.recovery.offline_runtimes == 1
    finally:
        app_main.get_config.cache_clear()
