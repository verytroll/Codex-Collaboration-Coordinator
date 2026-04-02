from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.reviews import ReviewRecord, ReviewRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'a2a_events.db').as_posix()}"


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


def test_public_a2a_event_stream_replay_and_ordering(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead",
                role="planner",
                is_lead=True,
            )
            session_id = _create_session(
                client,
                title="Public event stream",
                goal="Exercise public task events",
                lead_agent_id=lead_agent_id,
            )

            job_repository = JobRepository(database_url)
            artifact_repository = ArtifactRepository(database_url)
            review_repository = ReviewRepository(database_url)

            now = "2026-04-01T00:00:00Z"
            job = JobRecord(
                id="job_public_events",
                session_id=session_id,
                assigned_agent_id=lead_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Stream public events",
                instructions="Project this job into the public event surface",
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
            asyncio.run(job_repository.create(job))

            first_artifact = ArtifactRecord(
                id="art_public_events_1",
                job_id=job.id,
                session_id=session_id,
                source_message_id=None,
                artifact_type="final_text",
                title="Initial result",
                content_text="Initial result",
                file_path=None,
                file_name="initial.txt",
                mime_type="text/plain",
                size_bytes=len("Initial result".encode("utf-8")),
                checksum_sha256="checksum-public-events-1",
                metadata_json='{"kind":"initial"}',
                created_at=now,
                updated_at=now,
                channel_key="general",
            )
            asyncio.run(artifact_repository.create(first_artifact))

            create_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert create_response.status_code == 201
            task_id = create_response.json()["task"]["task_id"]

            subscription_response = client.post(
                f"/api/v1/a2a/tasks/{task_id}/subscriptions",
                json={"since_sequence": 0},
            )
            assert subscription_response.status_code == 201
            subscription = subscription_response.json()["subscription"]
            assert subscription["cursor_sequence"] == 0

            initial_events_response = client.get(
                f"/api/v1/a2a/tasks/{task_id}/events",
                params={"since_sequence": 0},
            )
            assert initial_events_response.status_code == 200
            initial_events = initial_events_response.json()["events"]
            assert [event["event_type"] for event in initial_events] == [
                "created",
                "artifact_attached",
            ]
            assert [event["sequence"] for event in initial_events] == [1, 2]
            assert initial_events[0]["task"]["api_version"] == "v1"

            review = ReviewRecord(
                id="rvw_public_events",
                session_id=session_id,
                source_job_id=job.id,
                reviewer_agent_id=lead_agent_id,
                requested_by_agent_id=lead_agent_id,
                review_scope="job",
                review_status="requested",
                review_channel_key="review",
                template_key="builder_to_reviewer",
                request_message_id=None,
                decision_message_id=None,
                summary_artifact_id=None,
                revision_job_id=None,
                request_payload_json='{"kind":"requested"}',
                decision_payload_json=None,
                requested_at=now,
                decided_at=None,
                created_at=now,
                updated_at=now,
            )
            asyncio.run(review_repository.create(review))

            updated_job = replace(
                job,
                status="input_required",
                result_summary="Waiting for review",
                started_at=now,
                updated_at="2026-04-01T00:01:00Z",
            )
            asyncio.run(job_repository.update(updated_job))
            second_artifact = ArtifactRecord(
                id="art_public_events_2",
                job_id=job.id,
                session_id=session_id,
                source_message_id=None,
                artifact_type="final_text",
                title="Review note",
                content_text="Needs review",
                file_path=None,
                file_name="review.txt",
                mime_type="text/plain",
                size_bytes=len("Needs review".encode("utf-8")),
                checksum_sha256="checksum-public-events-2",
                metadata_json='{"kind":"review"}',
                created_at="2026-04-01T00:01:00Z",
                updated_at="2026-04-01T00:01:00Z",
                channel_key="general",
            )
            asyncio.run(artifact_repository.create(second_artifact))

            refresh_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert refresh_response.status_code == 201

            events_response = client.get(
                f"/api/v1/a2a/tasks/{task_id}/events",
                params={"since_sequence": 0},
            )
            assert events_response.status_code == 200
            events = events_response.json()["events"]
            assert [event["event_type"] for event in events] == [
                "created",
                "artifact_attached",
                "status_changed",
                "review_requested",
                "artifact_attached",
            ]
            assert [event["sequence"] for event in events] == [1, 2, 3, 4, 5]
            assert events[1]["change"]["field"] == "artifact"
            assert events[2]["change"]["field"] == "status"
            assert events[3]["change"]["field"] == "review_requested"
            assert events[4]["change"]["artifact"]["id"] == second_artifact.id

            updated_completed_job = replace(
                updated_job,
                status="completed",
                completed_at="2026-04-01T00:02:00Z",
                updated_at="2026-04-01T00:02:00Z",
            )
            asyncio.run(job_repository.update(updated_completed_job))
            completion_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert completion_response.status_code == 201

            replay_response = client.get(
                f"/api/v1/a2a/tasks/{task_id}/events",
                params={"since_sequence": 5},
            )
            assert replay_response.status_code == 200
            replay_events = replay_response.json()["events"]
            assert [event["event_type"] for event in replay_events] == [
                "status_changed",
                "completed",
            ]
            assert [event["sequence"] for event in replay_events] == [6, 7]

            with client.stream("GET", f"/api/v1/a2a/tasks/{task_id}/stream") as stream_response:
                assert stream_response.status_code == 200
                assert stream_response.headers["content-type"].startswith("text/event-stream")
                stream_text = next(stream_response.iter_text())
                assert "event: a2a.public.task.events" in stream_text
                assert '"next_cursor_sequence": 7' in stream_text
                assert '"event_type": "created"' in stream_text
                assert '"event_type": "completed"' in stream_text
                assert '"id": "art_public_events_2"' in stream_text
    finally:
        app_main.get_config.cache_clear()
