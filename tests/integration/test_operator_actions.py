from __future__ import annotations

import asyncio
import json
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
from app.repositories.job_inputs import JobInputRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.phases import PhaseRecord, PhaseRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'operator_actions.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _seed_agent(
    database_url: str,
    *,
    agent_id: str,
    runtime_id: str,
    runtime_status: str = "offline",
) -> None:
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
                runtime_status=runtime_status,
                last_heartbeat_at=created_at if runtime_status != "offline" else None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(
    database_url: str,
    *,
    session_id: str,
    title: str,
    status: str = "active",
    active_phase_id: str | None,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title=title,
                goal=f"Goal for {title}",
                status=status,
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


def _seed_phase(
    database_url: str,
    *,
    phase_id: str,
    session_id: str,
    phase_key: str,
    is_default: int = 0,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        PhaseRepository(database_url).create(
            PhaseRecord(
                id=phase_id,
                session_id=session_id,
                phase_key=phase_key,
                title=phase_key.title(),
                description=None,
                relay_template_key=f"{phase_key}_template",
                default_channel_key="general",
                sort_order=10 if phase_key == "planning" else 20,
                is_default=is_default,
                created_at=created_at,
                updated_at=created_at,
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
    runtime_id: str | None = None,
    last_known_turn_status: str | None = None,
) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                channel_key="general",
                assigned_agent_id=agent_id,
                runtime_id=runtime_id,
                source_message_id=None,
                parent_job_id=None,
                title=f"Job {job_id}",
                instructions="Operator action test",
                status=status,
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status=last_known_turn_status or status,
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
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        ApprovalRepository(database_url).create(
            ApprovalRequestRecord(
                id=approval_id,
                job_id=job_id,
                agent_id=agent_id,
                approval_type="custom",
                status="pending",
                request_payload_json='{"scope":"operator"}',
                decision_payload_json=None,
                requested_at=created_at,
                resolved_at=None,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _action(client: TestClient, method: str, path: str, payload: dict[str, object] | None = None):
    response = client.request(method, path, json=payload)
    return response


def test_operator_actions_happy_path_duplicate_paths_and_audit(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent(database_url, agent_id="agt_lead", runtime_id="rt_lead")
    _seed_agent(database_url, agent_id="agt_builder", runtime_id="rt_builder")
    _seed_agent(database_url, agent_id="agt_reviewer", runtime_id="rt_reviewer")

    _seed_session(
        database_url,
        session_id="ses_operator",
        title="Operator",
        active_phase_id="ph_plan",
    )
    _seed_phase(
        database_url,
        phase_id="ph_plan",
        session_id="ses_operator",
        phase_key="planning",
        is_default=1,
    )
    _seed_phase(
        database_url,
        phase_id="ph_review",
        session_id="ses_operator",
        phase_key="review",
    )

    _seed_job(
        database_url,
        job_id="job_retry",
        session_id="ses_operator",
        agent_id="agt_builder",
        status="failed",
    )
    _seed_job(
        database_url,
        job_id="job_resume",
        session_id="ses_operator",
        agent_id="agt_builder",
        status="input_required",
    )
    _seed_job(
        database_url,
        job_id="job_cancel",
        session_id="ses_operator",
        agent_id="agt_builder",
        status="queued",
    )
    _seed_job(
        database_url,
        job_id="job_approve",
        session_id="ses_operator",
        agent_id="agt_reviewer",
        status="queued",
    )
    _seed_job(
        database_url,
        job_id="job_reject",
        session_id="ses_operator",
        agent_id="agt_reviewer",
        status="queued",
    )
    _seed_approval(
        database_url,
        approval_id="apr_approve",
        job_id="job_approve",
        agent_id="agt_reviewer",
    )
    _seed_approval(
        database_url,
        approval_id="apr_reject",
        job_id="job_reject",
        agent_id="agt_reviewer",
    )

    try:
        with TestClient(app) as client:
            retry_first = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_retry/retry",
                {"reason": "manual retry", "note": "retry after failure"},
            )
            assert retry_first.status_code == 200
            assert retry_first.json()["action"]["outcome"] == "applied"

            retry_second = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_retry/retry",
                {"reason": "manual retry"},
            )
            assert retry_second.status_code == 200
            assert retry_second.json()["action"]["outcome"] == "duplicate"

            resume_first = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_resume/resume",
                {"reason": "manual resume", "note": "resume after input"},
            )
            assert resume_first.status_code == 200
            assert resume_first.json()["action"]["outcome"] == "applied"

            resume_second = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_resume/resume",
                {"reason": "manual resume"},
            )
            assert resume_second.status_code == 200
            assert resume_second.json()["action"]["outcome"] == "duplicate"

            cancel_first = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_cancel/cancel",
                {"reason": "manual cancel"},
            )
            assert cancel_first.status_code == 200
            assert cancel_first.json()["action"]["outcome"] == "applied"
            assert cancel_first.json()["action"]["target_state_after"] == "canceled"

            cancel_second = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_cancel/cancel",
                {"reason": "manual cancel"},
            )
            assert cancel_second.status_code == 200
            assert cancel_second.json()["action"]["outcome"] == "duplicate"

            approve_response = _action(
                client,
                "POST",
                "/api/v1/operator/approvals/apr_approve/approve",
                {"reason": "approval accepted"},
            )
            assert approve_response.status_code == 200
            assert approve_response.json()["action"]["approval"]["status"] == "accepted"

            reject_response = _action(
                client,
                "POST",
                "/api/v1/operator/approvals/apr_reject/reject",
                {"reason": "approval rejected"},
            )
            assert reject_response.status_code == 200
            assert reject_response.json()["action"]["approval"]["status"] == "declined"

            phase_response = _action(
                client,
                "POST",
                "/api/v1/operator/sessions/ses_operator/phases/review/activate",
                {"reason": "move to review"},
            )
            assert phase_response.status_code == 200
            assert phase_response.json()["action"]["phase"]["phase_key"] == "review"

            session_events = asyncio.run(
                SessionEventRepository(database_url).list_by_session("ses_operator")
            )
            event_types = [event.event_type for event in session_events]
            assert "operator.action.retry" in event_types
            assert "operator.action.resume" in event_types
            assert "operator.action.cancel" in event_types
            assert "operator.action.approve" in event_types
            assert "operator.action.reject" in event_types
            assert "operator.action.activate_phase" in event_types
            operator_audits = [
                event for event in session_events if event.event_type.startswith("operator.action.")
            ]
            assert any(event.actor_type == "operator" for event in operator_audits)

            retry_inputs = asyncio.run(JobInputRepository(database_url).list_by_job("job_retry"))
            resume_inputs = asyncio.run(JobInputRepository(database_url).list_by_job("job_resume"))
            assert [item.input_type for item in retry_inputs] == ["retry"]
            assert [item.input_type for item in resume_inputs] == ["resume"]
    finally:
        app_main.get_config.cache_clear()


def test_operator_actions_reject_invalid_state_changes(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    _seed_agent(database_url, agent_id="agt_lead", runtime_id="rt_lead")
    _seed_session(
        database_url,
        session_id="ses_locked",
        title="Locked",
        status="draft",
        active_phase_id="ph_plan",
    )
    _seed_phase(
        database_url,
        phase_id="ph_plan",
        session_id="ses_locked",
        phase_key="planning",
        is_default=1,
    )
    _seed_job(
        database_url,
        job_id="job_running",
        session_id="ses_locked",
        agent_id="agt_lead",
        status="running",
    )

    try:
        with TestClient(app) as client:
            retry_conflict = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_running/retry",
                {"reason": "retry running job"},
            )
            assert retry_conflict.status_code == 409

            phase_conflict = _action(
                client,
                "POST",
                "/api/v1/operator/sessions/ses_locked/phases/planning/activate",
                {"reason": "activate planning"},
            )
            assert phase_conflict.status_code == 409

            cancelled = _action(
                client,
                "POST",
                "/api/v1/operator/jobs/job_running/cancel",
                {"reason": "cancel running"},
            )
            assert cancelled.status_code == 200

            session_events = asyncio.run(
                SessionEventRepository(database_url).list_by_session("ses_locked")
            )
            retry_failure = next(
                event for event in session_events if event.event_type == "operator.action.retry"
            )
            retry_payload = json.loads(retry_failure.event_payload_json or "{}")
            assert retry_payload["result"] == "failed"
            assert retry_payload["failure_mode"] == "invalid_state"
            phase_failure = next(
                event
                for event in session_events
                if event.event_type == "operator.action.activate_phase"
            )
            phase_payload = json.loads(phase_failure.event_payload_json or "{}")
            assert phase_payload["result"] == "failed"
            assert phase_payload["failure_mode"] == "inactive_session"
    finally:
        app_main.get_config.cache_clear()
