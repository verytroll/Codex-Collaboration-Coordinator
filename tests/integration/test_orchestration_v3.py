from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.session_events import SessionEventRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'orchestration_v3.db').as_posix()}"


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
        json={
            "lead_agent_id": lead_agent_id,
        },
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def _add_participant(
    client: TestClient,
    *,
    session_id: str,
    agent_id: str,
    role: str | None = None,
) -> None:
    payload: dict[str, object] = {"agent_id": agent_id}
    if role is not None:
        payload["role"] = role
    response = client.post(f"/api/v1/sessions/{session_id}/participants", json=payload)
    assert response.status_code == 201


def _seed_completed_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
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
                title="Implement feature",
                instructions="Build the feature and prepare it for review.",
                status="completed",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="completed",
                result_summary="Feature implemented",
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


def test_review_gate_revise_and_approval_finalize_flow(tmp_path, monkeypatch) -> None:
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
            builder_agent_id = _create_agent(
                client,
                display_name="Builder",
                role="builder",
                is_lead=False,
            )
            reviewer_agent_id = _create_agent(
                client,
                display_name="Reviewer",
                role="reviewer",
                is_lead=False,
            )
            session_id = _instantiate_session(client, lead_agent_id=lead_agent_id)
            _add_participant(
                client,
                session_id=session_id,
                agent_id=builder_agent_id,
                role="builder",
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=reviewer_agent_id,
                role="reviewer",
            )

            source_job_id = "job_orch_001"
            _seed_completed_job(
                database_url,
                job_id=source_job_id,
                session_id=session_id,
                agent_id=builder_agent_id,
                channel_key="implementation",
            )

            start_response = client.post(f"/api/v1/orchestration/sessions/{session_id}/start")
            assert start_response.status_code == 201
            assert start_response.json()["run"]["current_phase_key"] == "implementation"

            review_gate_response = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json={
                    "source_job_id": source_job_id,
                    "gate_type": "review_required",
                    "success_phase_key": "finalize",
                    "failure_phase_key": "revise",
                    "reviewer_agent_id": reviewer_agent_id,
                    "requested_by_agent_id": lead_agent_id,
                    "notes": "Check the implementation before finalization.",
                },
            )
            assert review_gate_response.status_code == 201
            review_gate_body = review_gate_response.json()
            review_id = review_gate_body["review_id"]
            assert review_gate_body["handoff_job_id"] is not None
            assert review_gate_body["run"]["gate_status"] == "pending"
            assert review_gate_body["run"]["pending_phase_key"] == "finalize"

            review_decision_response = client.post(
                f"/api/v1/reviews/{review_id}/decision",
                json={
                    "decision": "changes_requested",
                    "summary": "Needs one more pass.",
                    "required_changes": [
                        "Tighten error handling",
                        "Add an edge case test",
                    ],
                    "notes": "Return to the builder for revision.",
                    "revision_priority": "high",
                },
            )
            assert review_decision_response.status_code == 200
            review_decision = review_decision_response.json()["review"]
            revision_job_id = review_decision["revision_job_id"]
            assert revision_job_id is not None
            assert review_decision["summary_artifact_id"] is not None

            orchestration_response = client.get(f"/api/v1/orchestration/sessions/{session_id}")
            assert orchestration_response.status_code == 200
            orchestration_run = orchestration_response.json()["run"]
            assert orchestration_run["gate_status"] == "rejected"
            assert orchestration_run["current_phase_key"] == "revise"
            assert orchestration_run["revision_job_id"] == revision_job_id

            approval_gate_response = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json={
                    "source_job_id": revision_job_id,
                    "gate_type": "approval_required",
                    "success_phase_key": "finalize",
                    "failure_phase_key": "revise",
                    "approver_agent_id": lead_agent_id,
                    "requested_by_agent_id": lead_agent_id,
                    "notes": "Approve the revised implementation.",
                },
            )
            assert approval_gate_response.status_code == 201
            approval_gate_body = approval_gate_response.json()
            approval_id = approval_gate_body["approval_id"]
            assert approval_gate_body["handoff_job_id"] is not None
            assert approval_gate_body["run"]["gate_status"] == "pending"

            approval_response = client.post(
                f"/api/v1/approvals/{approval_id}/accept",
                json={"decision_payload": {"approved_by": lead_agent_id}},
            )
            assert approval_response.status_code == 200
            assert approval_response.json()["status"] == "accepted"

            finalized_run_response = client.get(f"/api/v1/orchestration/sessions/{session_id}")
            assert finalized_run_response.status_code == 200
            finalized_run = finalized_run_response.json()["run"]
            assert finalized_run["gate_status"] == "approved"
            assert finalized_run["current_phase_key"] == "finalize"
            assert finalized_run["status"] == "completed"
            assert finalized_run["decision_artifact_id"] is not None

            phases_response = client.get(f"/api/v1/sessions/{session_id}/phases")
            assert phases_response.status_code == 200
            active_phase = next(
                phase for phase in phases_response.json()["phases"] if phase["is_active"] is True
            )
            assert active_phase["phase_key"] == "finalize"

            event_repository = SessionEventRepository(database_url)
            events = asyncio.run(event_repository.list_by_session(session_id))
            assert {event.event_type for event in events} >= {
                "orchestration.review_requested",
                "orchestration.review.rejected",
                "orchestration.approval_requested",
                "orchestration.approval.accepted",
            }
    finally:
        app_main.get_config.cache_clear()
