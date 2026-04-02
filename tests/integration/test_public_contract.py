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
    return f"sqlite:///{(tmp_path / 'public_contract.db').as_posix()}"


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


def test_legacy_a2a_bridge_remains_compatible_but_not_advertised(tmp_path, monkeypatch) -> None:
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
                title="Public contract",
                goal="Exercise the public adoption baseline",
                lead_agent_id=lead_agent_id,
            )

            job_repository = JobRepository(database_url)
            artifact_repository = ArtifactRepository(database_url)
            now = "2026-04-02T00:00:00Z"
            job = JobRecord(
                id="job_public_contract",
                session_id=session_id,
                assigned_agent_id=lead_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Public contract job",
                instructions="Exercise the public v1 task surface",
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

            artifact = ArtifactRecord(
                id="art_public_contract",
                job_id=job.id,
                session_id=session_id,
                source_message_id=None,
                artifact_type="final_text",
                title="Contract note",
                content_text="Contract note",
                file_path=None,
                file_name="contract-note.txt",
                mime_type="text/plain",
                size_bytes=len("Contract note".encode("utf-8")),
                checksum_sha256="checksum-public-contract",
                metadata_json='{"kind":"contract"}',
                created_at=now,
                updated_at=now,
                channel_key="general",
            )
            asyncio.run(artifact_repository.create(artifact))

            agent_card = client.get("/.well-known/agent-card.json").json()
            endpoint_paths = {endpoint["path"] for endpoint in agent_card["endpoints"]}
            assert "/api/v1/a2a/jobs/{job_id}/project" not in endpoint_paths
            assert "/api/v1/a2a/sessions/{session_id}/tasks" not in endpoint_paths
            assert (
                "legacy adapter bridge routes remain available for compatibility only"
                in " ".join(agent_card["compatibility_notes"]).lower()
            )

            legacy_project_response = client.post(f"/api/v1/a2a/jobs/{job.id}/project")
            assert legacy_project_response.status_code == 201
            legacy_task = legacy_project_response.json()["task"]
            assert legacy_task["task_id"]
            assert legacy_task["status"] == "queued"
            assert legacy_task["artifacts"][0]["id"] == artifact.id

            legacy_list_response = client.get(f"/api/v1/a2a/sessions/{session_id}/tasks")
            assert legacy_list_response.status_code == 200
            assert [item["task_id"] for item in legacy_list_response.json()["tasks"]] == [
                legacy_task["task_id"]
            ]

            completed_job = replace(
                job,
                status="completed",
                result_summary="The public contract task completed successfully.",
                started_at="2026-04-02T00:01:00Z",
                completed_at="2026-04-02T00:02:00Z",
                updated_at="2026-04-02T00:02:00Z",
            )
            asyncio.run(job_repository.update(completed_job))
            asyncio.run(
                artifact_repository.create(
                    ArtifactRecord(
                        id="art_public_contract_complete",
                        job_id=job.id,
                        session_id=session_id,
                        source_message_id=None,
                        artifact_type="final_text",
                        title="Completion note",
                        content_text="The public contract task completed successfully.",
                        file_path=None,
                        file_name="completion.txt",
                        mime_type="text/plain",
                        size_bytes=len(
                            "The public contract task completed successfully.".encode("utf-8")
                        ),
                        checksum_sha256="checksum-public-contract-complete",
                        metadata_json='{"kind":"completion"}',
                        created_at="2026-04-02T00:02:00Z",
                        updated_at="2026-04-02T00:02:00Z",
                        channel_key="general",
                    )
                )
            )

            refresh_response = client.post(f"/api/v1/a2a/jobs/{job.id}/project")
            assert refresh_response.status_code == 201
            refreshed_task = refresh_response.json()["task"]
            assert refreshed_task["status"] == "completed"
            assert refreshed_task["job_id"] == job.id
            assert refreshed_task["summary"] == "The public contract task completed successfully."
            assert len(refreshed_task["artifacts"]) == 2

            direct_stream_response = client.get(
                f"/api/v1/a2a/tasks/{legacy_task['task_id']}/stream",
                headers={"Last-Event-ID": "0"},
            )
            assert direct_stream_response.status_code == 200
            assert direct_stream_response.headers["content-type"].startswith("text/event-stream")
            direct_stream_text = direct_stream_response.text
            assert "event: a2a.public.task.events" in direct_stream_text
            assert '"contract_version": "a2a.public.task.event.stream.v1"' in direct_stream_text
    finally:
        app_main.get_config.cache_clear()
