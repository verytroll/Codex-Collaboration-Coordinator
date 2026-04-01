from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'a2a_interoperability.db').as_posix()}"


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


def test_public_a2a_interoperability_smoke(tmp_path, monkeypatch) -> None:
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
                title="A2A interoperability",
                goal="Exercise the public A2A contract",
                lead_agent_id=lead_agent_id,
            )

            job_repository = JobRepository(database_url)
            artifact_repository = ArtifactRepository(database_url)
            now = "2026-04-01T00:00:00Z"
            job = JobRecord(
                id="job_public_interop",
                session_id=session_id,
                assigned_agent_id=lead_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Public interoperability job",
                instructions="Exercise the public A2A task surface",
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

            agent_card_response = client.get("/.well-known/agent-card.json")
            assert agent_card_response.status_code == 200
            agent_card = agent_card_response.json()
            assert agent_card["api_version"] == "v1"
            assert agent_card["contract_version"] == "a2a.agent-card.v1"
            assert agent_card["public_api_base_url"].endswith("/api/v1/a2a")
            endpoint_paths = {endpoint["path"] for endpoint in agent_card["endpoints"]}
            assert {
                "/api/v1/a2a/tasks",
                "/api/v1/a2a/tasks/{task_id}",
                "/api/v1/a2a/tasks/{task_id}/subscriptions",
                "/api/v1/a2a/tasks/{task_id}/events",
                "/api/v1/a2a/subscriptions/{subscription_id}/events",
            }.issubset(endpoint_paths)

            create_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert create_response.status_code == 201
            create_body = create_response.json()
            task = create_body["task"]
            assert task["api_version"] == "v1"
            assert task["contract_version"] == "a2a.public.task.v1"
            assert task["task_id"]
            assert task["status"]["state"] == "queued"
            assert task["summary"] == "Exercise the public A2A task surface"
            assert task["artifacts"] == []

            task_id = task["task_id"]
            list_response = client.get("/api/v1/a2a/tasks", params={"session_id": session_id})
            assert list_response.status_code == 200
            assert [item["task_id"] for item in list_response.json()["tasks"]] == [task_id]

            get_response = client.get(f"/api/v1/a2a/tasks/{task_id}")
            assert get_response.status_code == 200
            assert get_response.json() == create_body

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
            assert [event["event_type"] for event in initial_events] == ["created"]
            assert initial_events[0]["task"]["task_id"] == task_id

            completion_artifact = ArtifactRecord(
                id="art_public_interop_1",
                job_id=job.id,
                session_id=session_id,
                source_message_id=None,
                artifact_type="final_text",
                title="Completion note",
                content_text="The public task completed successfully.",
                file_path=None,
                file_name="completion.txt",
                mime_type="text/plain",
                size_bytes=len("The public task completed successfully.".encode("utf-8")),
                checksum_sha256="checksum-public-interop",
                metadata_json='{"kind":"completion"}',
                created_at="2026-04-01T00:01:00Z",
                updated_at="2026-04-01T00:01:00Z",
                channel_key="general",
            )
            asyncio.run(artifact_repository.create(completion_artifact))

            completed_job = replace(
                job,
                status="completed",
                result_summary="The public task completed successfully.",
                started_at="2026-04-01T00:00:30Z",
                completed_at="2026-04-01T00:01:00Z",
                updated_at="2026-04-01T00:01:00Z",
            )
            asyncio.run(job_repository.update(completed_job))

            refresh_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert refresh_response.status_code == 201
            refresh_body = refresh_response.json()
            refreshed_task = refresh_body["task"]
            assert refreshed_task["task_id"] == task_id
            assert refreshed_task["status"]["state"] == "completed"
            assert refreshed_task["summary"] == "The public task completed successfully."
            assert len(refreshed_task["artifacts"]) == 1
            assert refreshed_task["artifacts"][0]["is_primary"] is True

            replay_response = client.get(
                f"/api/v1/a2a/tasks/{task_id}/events",
                params={"since_sequence": 0},
            )
            assert replay_response.status_code == 200
            replay_body = replay_response.json()
            assert replay_body["since_sequence"] == 0
            assert [event["event_type"] for event in replay_body["events"]] == [
                "created",
                "status_changed",
                "artifact_attached",
                "completed",
            ]
            assert [event["sequence"] for event in replay_body["events"]] == [1, 2, 3, 4]
            assert replay_body["events"][1]["change"]["field"] == "status"
            assert replay_body["events"][2]["change"]["artifact"]["id"] == completion_artifact.id

            stream_response = client.get(
                f"/api/v1/a2a/subscriptions/{subscription['subscription_id']}/events"
            )
            assert stream_response.status_code == 200
            assert stream_response.headers["content-type"].startswith("text/event-stream")
            stream_text = stream_response.text
            assert "event: created" in stream_text
            assert "event: status_changed" in stream_text
            assert "event: artifact_attached" in stream_text
            assert "event: completed" in stream_text
            assert "id: 4" in stream_text
    finally:
        app_main.get_config.cache_clear()
