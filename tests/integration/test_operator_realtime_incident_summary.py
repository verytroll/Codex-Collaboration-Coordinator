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
from app.repositories.session_events import SessionEventRecord, SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'operator_realtime_incident.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent(database_url: str, *, agent_id: str, runtime_id: str) -> None:
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
                id=runtime_id,
                agent_id=agent_id,
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status="online",
                last_heartbeat_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(database_url: str, *, session_id: str, active_phase_id: str | None) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title="Incident Session",
                goal="Exercise incident summary rendering",
                status="active",
                lead_agent_id="agt_lead",
                active_phase_id=active_phase_id,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=created_at,
                template_key="template",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_job(database_url: str, *, job_id: str, session_id: str, agent_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                channel_key="general",
                assigned_agent_id=agent_id,
                runtime_id="rt_worker",
                source_message_id=None,
                parent_job_id=None,
                title="Blocked job",
                instructions="Investigate and recover the blocked job",
                status="failed",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="failed",
                result_summary=None,
                error_code="E_FAIL",
                error_message="Job failed during execution",
                started_at=created_at,
                completed_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_pending_approval(
    database_url: str, *, approval_id: str, job_id: str, agent_id: str
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        ApprovalRepository(database_url).create(
            ApprovalRequestRecord(
                id=approval_id,
                job_id=job_id,
                agent_id=agent_id,
                approval_type="custom",
                status="pending",
                request_payload_json='{"reason":"blocked by policy"}',
                decision_payload_json=None,
                requested_at=created_at,
                resolved_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session_event(database_url: str, *, session_id: str) -> None:
    created_at = "2026-04-01T00:01:00Z"
    asyncio.run(
        SessionEventRepository(database_url).create(
            SessionEventRecord(
                id="evt_operator_retry",
                session_id=session_id,
                event_type="operator.action.retry",
                actor_type="operator",
                actor_id="op_triage",
                event_payload_json=(
                    '{"target_type":"job","target_id":"job_blocked","reason":"manual triage"}'
                ),
                created_at=created_at,
            )
        )
    )


def _seed_loop_guard_event(database_url: str, *, session_id: str) -> None:
    created_at = "2026-04-01T00:01:00Z"
    asyncio.run(
        SessionEventRepository(database_url).create(
            SessionEventRecord(
                id="evt_loop_guard",
                session_id=session_id,
                event_type="loop_guard_triggered",
                actor_type="system",
                actor_id=None,
                event_payload_json='{"reason":"loop guard stopped the relay"}',
                created_at=created_at,
            )
        )
    )


def test_operator_activity_incident_summary(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent(database_url, agent_id="agt_lead", runtime_id="rt_lead")
    _seed_agent(database_url, agent_id="agt_worker", runtime_id="rt_worker")
    _seed_session(database_url, session_id="ses_incident", active_phase_id=None)
    _seed_job(database_url, job_id="job_blocked", session_id="ses_incident", agent_id="agt_worker")
    _seed_pending_approval(
        database_url,
        approval_id="apr_blocked",
        job_id="job_blocked",
        agent_id="agt_worker",
    )
    _seed_session_event(database_url, session_id="ses_incident")

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/operator/sessions/ses_incident/activity")
            assert response.status_code == 200
            payload = response.json()
            summary = payload["incident_summary"]
            assert summary["state"] == "incident"
            assert summary["severity"] == "critical"
            assert summary["headline"] == "Job job_blocked is in error"
            assert "retry" in summary["recommended_action"]
            assert summary["latest_actor"] == "operator:op_triage"
            assert summary["latest_event_type"] == "operator.action.retry"
            assert payload["signals"]["recent_errors"]
            assert payload["signals"]["pending_approvals"]
    finally:
        app_main.get_config.cache_clear()


def test_operator_activity_loop_guard_summary(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent(database_url, agent_id="agt_lead", runtime_id="rt_lead")
    _seed_session(database_url, session_id="ses_loop_guard", active_phase_id=None)
    _seed_loop_guard_event(database_url, session_id="ses_loop_guard")

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/operator/sessions/ses_loop_guard/activity")
            assert response.status_code == 200
            payload = response.json()
            summary = payload["incident_summary"]
            assert summary["state"] == "incident"
            assert summary["severity"] == "critical"
            assert summary["headline"] == "Loop guard triggered"
            assert "loop guard reason" in summary["recommended_action"]
            assert "Inspect the blocked job" not in summary["recommended_action"]
            assert summary["latest_reason"] == "loop guard stopped the relay"
            assert payload["signals"]["recent_errors"]
    finally:
        app_main.get_config.cache_clear()
