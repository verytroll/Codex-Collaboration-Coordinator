from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'a2a_public.db').as_posix()}"


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


def test_public_a2a_task_api_round_trip_and_mapping(tmp_path, monkeypatch) -> None:
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
                title="Public task API",
                goal="Exercise the public A2A contract",
                lead_agent_id=lead_agent_id,
            )

            job_repository = JobRepository(database_url)
            artifact_repository = ArtifactRepository(database_url)

            now = "2026-03-31T00:00:00Z"
            job = JobRecord(
                id="job_public_a2a",
                session_id=session_id,
                assigned_agent_id=lead_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Compile public task",
                instructions="Project this job into the public A2A surface",
                status="failed",
                hop_count=0,
                priority="high",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="failed",
                result_summary="Compilation failed",
                error_code="codex_timeout",
                error_message="Codex timed out",
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
                channel_key="general",
            )
            asyncio.run(job_repository.create(job))

            artifact = ArtifactRecord(
                id="art_public_a2a",
                job_id=job.id,
                session_id=session_id,
                source_message_id=None,
                artifact_type="final_text",
                title="Failure summary",
                content_text="Build failed",
                file_path=None,
                file_name="failure.txt",
                mime_type="text/plain",
                size_bytes=len("Build failed".encode("utf-8")),
                checksum_sha256="checksum-public-a2a",
                metadata_json='{"kind":"failure"}',
                created_at=now,
                updated_at=now,
                channel_key="general",
            )
            asyncio.run(artifact_repository.create(artifact))

            create_response = client.post("/api/v1/a2a/tasks", json={"job_id": job.id})
            assert create_response.status_code == 201
            create_body = create_response.json()
            assert set(create_body) == {"task"}
            task = create_body["task"]
            assert task["api_version"] == "v1"
            assert task["contract_version"] == "a2a.public.task.v1"
            assert task["job_id"] == job.id
            assert task["session_id"] == session_id
            assert task["context_id"] == session_id
            assert task["phase_key"] == "planning"
            assert task["phase_title"] == "Planning"
            assert task["phase_template_key"] == "planner_to_builder"
            assert task["relay_template_key"] == "planner_to_builder"
            assert task["status"] == {
                "state": "failed",
                "internal_status": "failed",
                "is_terminal": True,
                "is_blocked": False,
                "started_at": now,
                "completed_at": now,
                "updated_at": task["status"]["updated_at"],
            }
            assert task["error"] == {
                "code": "codex_timeout",
                "message": "Codex timed out",
                "details": {
                    "job_id": job.id,
                    "session_id": session_id,
                    "phase_key": "planning",
                    "assigned_agent_id": lead_agent_id,
                },
            }
            assert len(task["artifacts"]) == 1
            assert task["artifacts"][0] == {
                "id": artifact.id,
                "artifact_type": "final_text",
                "title": "Failure summary",
                "file_name": "failure.txt",
                "mime_type": "text/plain",
                "size_bytes": len("Build failed".encode("utf-8")),
                "checksum_sha256": "checksum-public-a2a",
                "channel_key": "general",
                "is_primary": True,
            }

            list_response = client.get("/api/v1/a2a/tasks", params={"session_id": session_id})
            assert list_response.status_code == 200
            list_body = list_response.json()
            assert [item["task_id"] for item in list_body["tasks"]] == [task["task_id"]]
            assert list_body["tasks"][0]["status"]["state"] == "failed"

            get_response = client.get(f"/api/v1/a2a/tasks/{task['task_id']}")
            assert get_response.status_code == 200
            assert get_response.json() == create_body
    finally:
        app_main.get_config.cache_clear()
