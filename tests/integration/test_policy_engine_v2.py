from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.jobs import JobRecord, JobRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'policy_engine_v2.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _create_agent(
    client: TestClient,
    *,
    display_name: str,
    role: str,
    is_lead: bool,
) -> str:
    response = client.post(
        "/api/v1/agents",
        json={
            "display_name": display_name,
            "role": role,
            "is_lead": is_lead,
            "runtime_kind": "codex",
            "runtime_config": {
                "workspace_path": "/workspace/project",
                "sandbox_mode": "workspace-write",
            },
        },
    )
    assert response.status_code == 201
    return response.json()["agent"]["id"]


def _instantiate_session(client: TestClient, *, lead_agent_id: str) -> str:
    response = client.post(
        "/api/v1/session-templates/implementation_review/instantiate",
        json={"lead_agent_id": lead_agent_id},
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def _seed_completed_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    title: str,
    channel_key: str = "general",
) -> None:
    job_repository = JobRepository(database_url)
    asyncio.run(
        job_repository.create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                assigned_agent_id=agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title=title,
                instructions=f"{title} instructions",
                status="completed",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="completed",
                result_summary=f"{title} done",
                error_code=None,
                error_message=None,
                started_at="2026-04-01T00:00:00Z",
                completed_at="2026-04-01T00:05:00Z",
                created_at="2026-04-01T00:00:00Z",
                updated_at="2026-04-01T00:05:00Z",
                channel_key=channel_key,
            )
        )
    )


def _create_policy(
    client: TestClient,
    *,
    session_id: str,
    template_key: str,
    phase_key: str,
    policy_type: str,
    name: str,
    decision: str,
) -> str:
    response = client.post(
        "/api/v1/policies",
        json={
            "session_id": session_id,
            "template_key": template_key,
            "phase_key": phase_key,
            "policy_type": policy_type,
            "name": name,
            "description": name,
            "priority": 10,
            "is_active": True,
            "automation_paused": False,
            "conditions": {
                "gate_type": "approval_required",
                "template_key": template_key,
                "phase_key": phase_key,
            },
            "actions": {
                "decision": decision,
                "reason": name,
            },
        },
    )
    assert response.status_code == 201
    return response.json()["policy"]["id"]


def test_policy_auto_approves_finalize_gate(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead Planner",
                role="planner",
                is_lead=True,
            )
            session_id = _instantiate_session(client, lead_agent_id=lead_agent_id)
            _seed_completed_job(
                database_url,
                job_id="job_auto_001",
                session_id=session_id,
                agent_id=lead_agent_id,
                title="Auto approve source",
            )
            policy_id = _create_policy(
                client,
                session_id=session_id,
                template_key="implementation_review",
                phase_key="finalize",
                policy_type="conditional_auto_approve",
                name="Auto approve finalize",
                decision="auto_approve",
            )

            gate_response = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json={
                    "source_job_id": "job_auto_001",
                    "gate_type": "approval_required",
                    "success_phase_key": "finalize",
                    "failure_phase_key": "revise",
                    "approver_agent_id": lead_agent_id,
                    "requested_by_agent_id": lead_agent_id,
                    "notes": "Auto approval should complete this gate.",
                },
            )
            assert gate_response.status_code == 201
            gate_body = gate_response.json()
            assert gate_body["review_id"] is None
            assert gate_body["approval_id"] is not None
            assert gate_body["handoff_job_id"] is not None
            assert gate_body["run"]["gate_status"] == "approved"
            assert gate_body["run"]["status"] == "completed"

            approval_job_response = client.get(f"/api/v1/jobs/{gate_body['handoff_job_id']}")
            assert approval_job_response.status_code == 200
            approval_job = approval_job_response.json()["job"]
            assert approval_job["approvals"][0]["status"] == "accepted"

            decisions_response = client.get(f"/api/v1/policies/{policy_id}/decisions")
            assert decisions_response.status_code == 200
            assert [
                decision["decision"] for decision in decisions_response.json()["decisions"]
            ] == ["auto_approve"]
    finally:
        app_main.get_config.cache_clear()


def test_policy_escalates_approval_into_review(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead Planner",
                role="planner",
                is_lead=True,
            )
            session_id = _instantiate_session(client, lead_agent_id=lead_agent_id)
            _seed_completed_job(
                database_url,
                job_id="job_escalate_001",
                session_id=session_id,
                agent_id=lead_agent_id,
                title="Escalate source",
            )
            policy_id = _create_policy(
                client,
                session_id=session_id,
                template_key="implementation_review",
                phase_key="finalize",
                policy_type="escalation",
                name="Escalate into review",
                decision="escalate_review",
            )

            gate_response = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json={
                    "source_job_id": "job_escalate_001",
                    "gate_type": "approval_required",
                    "success_phase_key": "finalize",
                    "failure_phase_key": "revise",
                    "approver_agent_id": lead_agent_id,
                    "requested_by_agent_id": lead_agent_id,
                    "notes": "This should escalate to review.",
                },
            )
            assert gate_response.status_code == 201
            gate_body = gate_response.json()
            assert gate_body["approval_id"] is None
            assert gate_body["review_id"] is not None
            assert gate_body["run"]["gate_type"] == "review_required"
            assert gate_body["run"]["gate_status"] == "pending"

            review_response = client.get(f"/api/v1/reviews/{gate_body['review_id']}")
            assert review_response.status_code == 200
            assert review_response.json()["review"]["review_status"] == "requested"

            decisions_response = client.get(f"/api/v1/policies/{policy_id}/decisions")
            decisions = decisions_response.json()["decisions"]
            assert [decision["decision"] for decision in decisions] == ["escalate_review"]
    finally:
        app_main.get_config.cache_clear()


def test_policy_pause_and_resume_controls_automation(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead Planner",
                role="planner",
                is_lead=True,
            )
            session_id = _instantiate_session(client, lead_agent_id=lead_agent_id)
            _seed_completed_job(
                database_url,
                job_id="job_pause_001",
                session_id=session_id,
                agent_id=lead_agent_id,
                title="Paused source",
            )
            policy_id = _create_policy(
                client,
                session_id=session_id,
                template_key="implementation_review",
                phase_key="finalize",
                policy_type="conditional_auto_approve",
                name="Pauseable auto approve",
                decision="auto_approve",
            )

            pause_response = client.post(
                f"/api/v1/policies/{policy_id}/pause",
                json={"reason": "operator maintenance"},
            )
            assert pause_response.status_code == 200
            assert pause_response.json()["policy"]["automation_paused"] is True

            first_gate_response = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json={
                    "source_job_id": "job_pause_001",
                    "gate_type": "approval_required",
                    "success_phase_key": "finalize",
                    "failure_phase_key": "revise",
                    "approver_agent_id": lead_agent_id,
                    "requested_by_agent_id": lead_agent_id,
                    "notes": "Policy is paused, so this should remain manual.",
                },
            )
            assert first_gate_response.status_code == 201
            first_gate_body = first_gate_response.json()
            assert first_gate_body["approval_id"] is not None
            assert first_gate_body["run"]["gate_status"] == "pending"

            first_job_response = client.get(f"/api/v1/jobs/{first_gate_body['handoff_job_id']}")
            assert first_job_response.status_code == 200
            assert first_job_response.json()["job"]["approvals"][0]["status"] == "pending"

            accept_response = client.post(
                f"/api/v1/approvals/{first_gate_body['approval_id']}/accept",
                json={"decision_payload": {"manual_override": True}},
            )
            assert accept_response.status_code == 200
            assert accept_response.json()["status"] == "accepted"

            resume_response = client.post(
                f"/api/v1/policies/{policy_id}/resume",
                json={"reason": "operator maintenance complete"},
            )
            assert resume_response.status_code == 200
            assert resume_response.json()["policy"]["automation_paused"] is False

            _seed_completed_job(
                database_url,
                job_id="job_pause_002",
                session_id=session_id,
                agent_id=lead_agent_id,
                title="Resumed source",
            )
            second_gate_response = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json={
                    "source_job_id": "job_pause_002",
                    "gate_type": "approval_required",
                    "success_phase_key": "finalize",
                    "failure_phase_key": "revise",
                    "approver_agent_id": lead_agent_id,
                    "requested_by_agent_id": lead_agent_id,
                    "notes": "Policy is resumed and should auto approve again.",
                },
            )
            assert second_gate_response.status_code == 201
            second_gate_body = second_gate_response.json()
            assert second_gate_body["approval_id"] is not None
            assert second_gate_body["run"]["gate_status"] == "approved"
            assert second_gate_body["run"]["status"] == "completed"

            second_job_response = client.get(f"/api/v1/jobs/{second_gate_body['handoff_job_id']}")
            assert second_job_response.status_code == 200
            assert second_job_response.json()["job"]["approvals"][0]["status"] == "accepted"

            decisions_response = client.get(f"/api/v1/policies/{policy_id}/decisions")
            decisions = [
                decision["decision"] for decision in decisions_response.json()["decisions"]
            ]
            assert decisions == ["paused", "allow", "resumed", "auto_approve"]
    finally:
        app_main.get_config.cache_clear()
