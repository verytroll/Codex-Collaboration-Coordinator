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
    return f"sqlite:///{(tmp_path / 'public_streaming.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _create_agent(client: TestClient, *, display_name: str, role: str, is_lead: bool) -> str:
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


def test_public_task_stream_resumes_from_last_event_id(tmp_path, monkeypatch) -> None:
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
                title="Public streaming",
                goal="Exercise the public stream transport",
                lead_agent_id=lead_agent_id,
            )
            job_repository = JobRepository(database_url)
            artifact_repository = ArtifactRepository(database_url)
            now = "2026-04-01T00:00:00Z"
            job = JobRecord(
                id="job_public_stream",
                session_id=session_id,
                assigned_agent_id=lead_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Public stream job",
                instructions="Exercise public SSE transport",
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
                id="art_public_stream_1",
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
                checksum_sha256="checksum-public-stream-1",
                metadata_json='{"kind":"initial"}',
                created_at=now,
                updated_at=now,
                channel_key="general",
            )
            asyncio.run(artifact_repository.create(first_artifact))

            create_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert create_response.status_code == 201
            task_id = create_response.json()["task"]["task_id"]

            bootstrap = client.get(
                f"/api/v1/a2a/tasks/{task_id}/events",
                params={"since_sequence": 0},
            )
            assert bootstrap.status_code == 200
            cursor = bootstrap.json()["events"][-1]["sequence"]

            updated_job = replace(
                job,
                status="completed",
                result_summary="The public task completed successfully.",
                started_at="2026-04-01T00:00:30Z",
                completed_at="2026-04-01T00:01:00Z",
                updated_at="2026-04-01T00:01:00Z",
            )
            asyncio.run(job_repository.update(updated_job))
            asyncio.run(
                artifact_repository.create(
                    ArtifactRecord(
                        id="art_public_stream_2",
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
                        checksum_sha256="checksum-public-stream-2",
                        metadata_json='{"kind":"completion"}',
                        created_at="2026-04-01T00:01:00Z",
                        updated_at="2026-04-01T00:01:00Z",
                        channel_key="general",
                    )
                )
            )
            refresh_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert refresh_response.status_code == 201

            with client.stream(
                "GET",
                f"/api/v1/a2a/tasks/{task_id}/stream",
                params={"since_sequence": 0},
                headers={"Last-Event-ID": str(cursor)},
            ) as stream_response:
                assert stream_response.status_code == 200
                assert stream_response.headers["content-type"].startswith("text/event-stream")
                frame = next(stream_response.iter_text())
                assert "event: a2a.public.task.events" in frame
                assert '"next_cursor_sequence":' in frame
                assert '"event_type": "status_changed"' in frame
    finally:
        app_main.get_config.cache_clear()
