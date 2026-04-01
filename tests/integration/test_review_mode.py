from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

import app.main as app_main
from app.api.dependencies import get_codex_bridge_client
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.messages import MessageRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.session_events import SessionEventRepository


class FakeBridge:
    """Deterministic bridge for review integration tests."""

    async def thread_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {"result": {"thread_id": "thr_review"}}

    async def thread_resume(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {"result": {"thread_id": "thr_review", "resumed": True}}

    async def turn_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "result": {
                "turn_id": "turn_review",
                "status": "running",
                "output_text": "Review bridge output",
            }
        }

    async def turn_interrupt(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {"result": {"turn_id": params.get("turn_id") if params else None}}

    async def thread_compact_start(
        self, params: dict[str, object] | None = None
    ) -> dict[str, object]:
        return {"result": {"thread_id": "thr_review", "compacted": True}}


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'review_mode.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _build_app() -> tuple[object, FakeBridge]:
    app_main.get_config.cache_clear()
    app = app_main.create_app()
    bridge = FakeBridge()
    app.dependency_overrides[get_codex_bridge_client] = lambda: bridge
    return app, bridge


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


def _create_session(client: TestClient, *, title: str, goal: str, lead_agent_id: str) -> str:
    response = client.post(
        "/api/v1/sessions",
        json={
            "title": title,
            "goal": goal,
            "lead_agent_id": lead_agent_id,
        },
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def _add_participant(
    client: TestClient, *, session_id: str, agent_id: str, role: str | None = None
) -> None:
    payload: dict[str, object] = {"agent_id": agent_id}
    if role is not None:
        payload["role"] = role
    response = client.post(f"/api/v1/sessions/{session_id}/participants", json=payload)
    assert response.status_code == 201


def test_review_command_request_and_decision_flow(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app, bridge = _build_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(client, display_name="Lead", role="planner", is_lead=True)
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
            session_id = _create_session(
                client,
                title="Review mode",
                goal="Exercise review workflow",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(client, session_id=session_id, agent_id=lead_agent_id, role="planner")
            _add_participant(
                client, session_id=session_id, agent_id=builder_agent_id, role="builder"
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=reviewer_agent_id,
                role="reviewer",
            )

            job_repository = JobRepository(database_url)
            artifact_repository = ArtifactRepository(database_url)
            message_repository = MessageRepository(database_url)
            review_repository = ReviewRepository(database_url)
            session_event_repository = SessionEventRepository(database_url)

            job = JobRecord(
                id="job_review_001",
                session_id=session_id,
                assigned_agent_id=builder_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Implement feature",
                instructions="Build the feature and keep tests green.",
                status="completed",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="completed",
                result_summary="Implemented feature",
                error_code=None,
                error_message=None,
                started_at="2026-03-31T00:00:00Z",
                completed_at="2026-03-31T00:10:00Z",
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:10:00Z",
                channel_key="planning",
            )
            asyncio.run(job_repository.create(job))
            asyncio.run(
                artifact_repository.create(
                    ArtifactRecord(
                        id="art_review_001",
                        job_id=job.id,
                        session_id=session_id,
                        source_message_id=None,
                        artifact_type="final_text",
                        title="Implementation summary",
                        content_text="Implemented the feature and covered the path.",
                        file_path=None,
                        file_name="job_review_001-output.txt",
                        mime_type="text/plain",
                        size_bytes=len(
                            "Implemented the feature and covered the path.".encode("utf-8")
                        ),
                        checksum_sha256="checksum-review-001",
                        metadata_json=json.dumps(
                            {
                                "artifact_kind": "final_text",
                                "job_id": job.id,
                                "session_id": session_id,
                            },
                            sort_keys=True,
                        ),
                        created_at="2026-03-31T00:10:00Z",
                        updated_at="2026-03-31T00:10:00Z",
                        channel_key="planning",
                    )
                )
            )

            review_command_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": lead_agent_id,
                    "content": "/review #builder manual review pass",
                    "reply_to_message_id": None,
                    "channel_key": "general",
                },
            )
            assert review_command_response.status_code == 202
            review_command_body = review_command_response.json()
            assert review_command_body["message"]["message_type"] == "command"
            assert review_command_body["routing"]["created_jobs"] == []

            reviews = asyncio.run(review_repository.list_by_session(session_id))
            assert len(reviews) == 1
            review = reviews[0]
            assert review.source_job_id == job.id
            assert review.reviewer_agent_id == reviewer_agent_id
            assert review.review_status == "requested"

            template_response = client.get("/api/v1/review/templates")
            assert template_response.status_code == 200
            assert {
                template["template_key"] for template in template_response.json()["templates"]
            } == {
                "planner_to_builder",
                "builder_to_reviewer",
                "reviewer_to_builder_revise",
            }

            review_detail_response = client.get(f"/api/v1/reviews/{review.id}")
            assert review_detail_response.status_code == 200
            review_detail = review_detail_response.json()["review"]
            assert review_detail["request_payload"]["template_key"] == "builder_to_reviewer"
            assert (
                review_detail["request_payload"]["metadata"]["reviewer_agent_id"]
                == reviewer_agent_id
            )

            request_message = asyncio.run(message_repository.get(review.request_message_id))
            assert request_message is not None
            assert request_message.channel_key == "review"
            assert request_message.message_type == "status"

            decision_response = client.post(
                f"/api/v1/reviews/{review.id}/decision",
                json={
                    "decision": "changes_requested",
                    "summary": "Needs tighter error handling.",
                    "required_changes": [
                        "Add explicit validation for missing input",
                        "Cover edge cases in tests",
                    ],
                    "notes": "Focus on failure branches.",
                    "revision_priority": "high",
                },
            )
            assert decision_response.status_code == 200
            decision_review = decision_response.json()["review"]
            assert decision_review["review_status"] == "changes_requested"
            assert decision_review["summary_artifact_id"] is not None
            assert decision_review["revision_job_id"] is not None

            revised_job = asyncio.run(job_repository.get(decision_review["revision_job_id"]))
            assert revised_job is not None
            assert revised_job.parent_job_id == job.id
            assert revised_job.channel_key == "review"
            assert revised_job.status in {"queued", "running"}

            summary_artifact = asyncio.run(
                artifact_repository.get(decision_review["summary_artifact_id"])
            )
            assert summary_artifact is not None
            assert summary_artifact.artifact_type == "json"
            assert "review_summary" in (summary_artifact.metadata_json or "")

            decision_message = asyncio.run(
                message_repository.get(decision_review["decision_message_id"])
            )
            assert decision_message is not None
            assert decision_message.channel_key == "review"
            assert decision_message.message_type == "artifact_notice"

            events = asyncio.run(session_event_repository.list_by_session(session_id))
            assert {event.event_type for event in events} >= {
                "command.review",
                "review.requested",
                "review.decision.recorded",
            }
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()
