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
from app.repositories.phases import PhaseRecord, PhaseRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'operator_rbac.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


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
                title="RBAC",
                goal="RBAC",
                status="active",
                lead_agent_id="agt_lead",
                active_phase_id="ph_plan",
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=created_at,
                template_key="template",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_phase(database_url: str, *, session_id: str, phase_id: str, phase_key: str) -> None:
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
                sort_order=10,
                is_default=1 if phase_key == "planning" else 0,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_job(database_url: str, *, job_id: str, session_id: str, status: str) -> None:
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
                title=f"Job {job_id}",
                instructions="RBAC",
                status=status,
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
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


def _seed_approval(database_url: str, *, approval_id: str, job_id: str) -> None:
    created_at = "2026-04-01T00:00:00Z"
    asyncio.run(
        ApprovalRepository(database_url).create(
            ApprovalRequestRecord(
                id=approval_id,
                job_id=job_id,
                agent_id="agt_builder",
                approval_type="custom",
                status="pending",
                request_payload_json="{}",
                decision_payload_json=None,
                requested_at=created_at,
                resolved_at=None,
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
    access_token: str,
) -> str:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ACCESS_BOUNDARY_MODE", access_boundary_mode)
    monkeypatch.setenv("ACCESS_TOKEN", access_token)
    monkeypatch.delenv("ACCESS_TOKEN_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ID_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_ROLE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_TYPE_HEADER", raising=False)
    monkeypatch.delenv("ACTOR_LABEL_HEADER", raising=False)
    app_main.get_config.cache_clear()
    _migrate(database_url)
    return database_url


def test_operator_rbac_enforces_roles_and_missing_identity(tmp_path, monkeypatch) -> None:
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
    _seed_session(database_url, session_id="ses_rbac")
    _seed_phase(database_url, session_id="ses_rbac", phase_id="ph_plan", phase_key="planning")
    _seed_job(database_url, job_id="job_retry", session_id="ses_rbac", status="failed")
    _seed_job(database_url, job_id="job_review", session_id="ses_rbac", status="queued")
    _seed_approval(database_url, approval_id="apr_review", job_id="job_review")

    try:
        with TestClient(app) as client:
            retry_allowed = client.post(
                "/api/v1/operator/jobs/job_retry/retry",
                headers={
                    "X-Access-Token": "service-token",
                    "X-Actor-Id": "ops_01",
                    "X-Actor-Role": "operator",
                    "X-Actor-Type": "human",
                    "X-Actor-Label": "Oncall operator",
                },
                json={"reason": "retry"},
            )
            assert retry_allowed.status_code == 200

            retry_forbidden = client.post(
                "/api/v1/operator/jobs/job_retry/retry",
                headers={
                    "X-Access-Token": "service-token",
                    "X-Actor-Id": "rev_01",
                    "X-Actor-Role": "reviewer",
                    "X-Actor-Type": "human",
                    "X-Actor-Label": "Reviewer",
                },
                json={"reason": "retry"},
            )
            assert retry_forbidden.status_code == 403

            approval_allowed = client.post(
                "/api/v1/approvals/apr_review/accept",
                headers={
                    "X-Access-Token": "service-token",
                    "X-Actor-Id": "rev_01",
                    "X-Actor-Role": "reviewer",
                    "X-Actor-Type": "human",
                    "X-Actor-Label": "Reviewer",
                },
                json={"decision_payload": {"reason": "reviewed"}},
            )
            assert approval_allowed.status_code == 200

            missing_identity = client.post(
                "/api/v1/operator/jobs/job_retry/retry",
                headers={"X-Access-Token": "service-token"},
                json={"reason": "retry"},
            )
            assert missing_identity.status_code == 401

            session_events = asyncio.run(
                SessionEventRepository(database_url).list_by_session("ses_rbac")
            )
            operator_event = next(
                event for event in session_events if event.event_type == "operator.action.retry"
            )
            assert operator_event.actor_type == "operator"
            assert operator_event.actor_id == "ops_01"
            payload = operator_event.event_payload_json or ""
            assert "actor_role" in payload
    finally:
        app_main.get_config.cache_clear()
