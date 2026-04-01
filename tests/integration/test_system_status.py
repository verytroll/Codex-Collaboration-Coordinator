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
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'system.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent(
    database_url: str,
    *,
    agent_id: str,
    runtime_id: str,
    runtime_status: str,
    heartbeat_at: str | None = "2026-03-31T00:00:00Z",
) -> None:
    created_at = "2026-03-31T00:00:00Z"
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
                id=runtime_id,
                agent_id=agent_id,
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status=runtime_status,
                last_heartbeat_at=heartbeat_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(database_url: str, *, session_id: str, status: str) -> None:
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title=f"Session {session_id}",
                goal="Observe state",
                status=status,
                lead_agent_id="agt_1",
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at="2026-03-31T00:00:00Z",
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )


def _seed_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    status: str,
    thread_id: str,
) -> None:
    created_at = "2026-03-31T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                assigned_agent_id=agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title=f"Job {job_id}",
                instructions="Observe queue",
                status=status,
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=thread_id,
                active_turn_id=f"turn_{job_id}",
                last_known_turn_status=status,
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


def _seed_approval(database_url: str, *, approval_id: str, job_id: str, agent_id: str) -> None:
    created_at = "2026-03-31T00:00:00Z"
    asyncio.run(
        ApprovalRepository(database_url).create(
            ApprovalRequestRecord(
                id=approval_id,
                job_id=job_id,
                agent_id=agent_id,
                approval_type="custom",
                status="pending",
                request_payload_json='{"command":"pytest"}',
                decision_payload_json=None,
                requested_at=created_at,
                resolved_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def test_system_status_and_debug_surface(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent(database_url, agent_id="agt_1", runtime_id="rt_1", runtime_status="online")
    _seed_agent(
        database_url,
        agent_id="agt_2",
        runtime_id="rt_2",
        runtime_status="offline",
        heartbeat_at=None,
    )
    _seed_session(database_url, session_id="ses_active", status="active")
    _seed_session(database_url, session_id="ses_paused", status="paused")
    _seed_job(
        database_url,
        job_id="job_queued",
        session_id="ses_active",
        agent_id="agt_1",
        status="queued",
        thread_id="thr_q",
    )
    _seed_job(
        database_url,
        job_id="job_running",
        session_id="ses_active",
        agent_id="agt_1",
        status="running",
        thread_id="thr_r",
    )
    _seed_job(
        database_url,
        job_id="job_input",
        session_id="ses_active",
        agent_id="agt_2",
        status="input_required",
        thread_id="thr_i",
    )
    _seed_approval(database_url, approval_id="apr_1", job_id="job_input", agent_id="agt_2")

    try:
        with TestClient(app) as client:
            status_response = client.get("/api/v1/system/status")
            assert status_response.status_code == 200
            status_payload = status_response.json()
            assert status_payload["app"]["name"] == app.title
            assert status_payload["aggregates"]["active_sessions"] == 1
            assert status_payload["aggregates"]["registered_agents"] == 2
            assert status_payload["aggregates"]["jobs"]["queued"] == 1
            assert status_payload["aggregates"]["jobs"]["running"] == 1
            assert status_payload["aggregates"]["jobs"]["input_required"] == 1
            assert status_payload["aggregates"]["pending_approvals"] == 1
            assert status_payload["aggregates"]["runtimes_by_status"] == {
                "offline": 1,
                "online": 1,
            }
            assert status_payload["checks"]["db"]["status"] == "ok"
            assert status_payload["status"] == "degraded"
            assert any("queued job" in item for item in status_payload["diagnostics"])
            assert any("pending operator action" in item for item in status_payload["diagnostics"])

            debug_response = client.get("/api/v1/system/debug")
            assert debug_response.status_code == 200
            debug_payload = debug_response.json()
            assert debug_payload["runtime_statuses"] == {"offline": 1, "online": 1}
            assert [item["id"] for item in debug_payload["active_sessions"]] == ["ses_active"]
            assert [item["id"] for item in debug_payload["queued_jobs"]] == ["job_queued"]
            assert [item["id"] for item in debug_payload["running_jobs"]] == ["job_running"]
            assert [item["id"] for item in debug_payload["blocked_jobs"]] == ["job_input"]
            assert [item["id"] for item in debug_payload["pending_approvals"]] == ["apr_1"]
            assert any("no heartbeat timestamp" in item for item in debug_payload["diagnostics"])
    finally:
        app_main.get_config.cache_clear()
