from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'phases_a2a.db').as_posix()}"


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
    session = response.json()["session"]
    assert session["active_phase_id"] is not None
    return session["id"]


def _add_participant(client: TestClient, *, session_id: str, agent_id: str, role: str) -> None:
    response = client.post(
        f"/api/v1/sessions/{session_id}/participants",
        json={"agent_id": agent_id, "role": role},
    )
    assert response.status_code == 201


def test_phase_api_and_phase_aware_new_jobs(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(client, display_name="Lead", role="planner", is_lead=True)
            builder_agent_id = _create_agent(
                client,
                display_name="Builder",
                role="builder",
                is_lead=False,
            )
            session_id = _create_session(
                client,
                title="Phase aware",
                goal="Exercise phase presets",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(client, session_id=session_id, agent_id=lead_agent_id, role="planner")
            _add_participant(
                client,
                session_id=session_id,
                agent_id=builder_agent_id,
                role="builder",
            )

            offline_response = client.post(
                f"/api/v1/agents/{builder_agent_id}/heartbeat",
                json={"presence": "offline"},
            )
            assert offline_response.status_code == 201

            presets_response = client.get("/api/v1/phases/presets")
            assert presets_response.status_code == 200
            assert [preset["phase_key"] for preset in presets_response.json()["presets"]] == [
                "planning",
                "implementation",
                "review",
                "revise",
                "finalize",
            ]

            phases_response = client.get(f"/api/v1/sessions/{session_id}/phases")
            assert phases_response.status_code == 200
            phases = phases_response.json()["phases"]
            assert [phase["phase_key"] for phase in phases] == [
                "planning",
                "implementation",
                "review",
                "revise",
                "finalize",
            ]
            assert phases[0]["is_active"] is True

            planning_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": lead_agent_id,
                    "content": "/new #builder implement phase-aware relay",
                    "reply_to_message_id": None,
                    "channel_key": "general",
                },
            )
            assert planning_message_response.status_code == 202

            job_repository = JobRepository(database_url)
            planning_job = asyncio.run(job_repository.list_by_session(session_id))[-1]
            assert "planner_to_builder" in planning_job.instructions
            assert "phase_key" in planning_job.instructions
            assert "planning" in planning_job.instructions

            activate_response = client.post(f"/api/v1/sessions/{session_id}/phases/review/activate")
            assert activate_response.status_code == 200
            assert activate_response.json()["phase"]["phase_key"] == "review"

            refreshed_phases_response = client.get(f"/api/v1/sessions/{session_id}/phases")
            assert refreshed_phases_response.status_code == 200
            refreshed_phases = refreshed_phases_response.json()["phases"]
            assert (
                next(phase for phase in refreshed_phases if phase["phase_key"] == "review")[
                    "is_active"
                ]
                is True
            )

            review_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": lead_agent_id,
                    "content": "/new #builder prepare the review handoff",
                    "reply_to_message_id": None,
                    "channel_key": "general",
                },
            )
            assert review_message_response.status_code == 202

            review_job = asyncio.run(job_repository.list_by_session(session_id))[-1]
            assert "builder_to_reviewer" in review_job.instructions
            assert "phase_key" in review_job.instructions
            assert "review" in review_job.instructions

            finalize_activate_response = client.post(
                f"/api/v1/sessions/{session_id}/phases/finalize/activate"
            )
            assert finalize_activate_response.status_code == 200
            assert finalize_activate_response.json()["phase"]["phase_key"] == "finalize"

            finalize_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": lead_agent_id,
                    "content": "/new #builder wrap up the work",
                    "reply_to_message_id": None,
                    "channel_key": "general",
                },
            )
            assert finalize_message_response.status_code == 202

            finalize_job = asyncio.run(job_repository.list_by_session(session_id))[-1]
            assert "builder_to_reviewer" in finalize_job.instructions
            assert finalize_job.channel_key == "general"
            assert "phase_key" in finalize_job.instructions
            assert "finalize" in finalize_job.instructions

            artifact_repository = ArtifactRepository(database_url)
            asyncio.run(
                artifact_repository.create(
                    ArtifactRecord(
                        id="art_phase_001",
                        job_id=finalize_job.id,
                        session_id=session_id,
                        source_message_id=finalize_job.source_message_id,
                        artifact_type="json",
                        title="Phase handoff artifact",
                        content_text='{"ok": true}',
                        file_path=None,
                        file_name="phase-handoff.json",
                        mime_type="application/json",
                        size_bytes=len('{"ok": true}'.encode("utf-8")),
                        checksum_sha256="phase-checksum",
                        metadata_json='{"kind":"a2a_preview"}',
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:00:00Z",
                        channel_key=finalize_job.channel_key,
                    )
                )
            )

            project_response = client.post(f"/api/v1/a2a/jobs/{finalize_job.id}/project")
            assert project_response.status_code == 201
            task = project_response.json()["task"]
            assert task["job_id"] == finalize_job.id
            assert task["phase_key"] == "finalize"
            assert task["status"] == "queued"
            assert len(task["artifacts"]) == 1

            get_task_response = client.get(f"/api/v1/a2a/tasks/{task['task_id']}")
            assert get_task_response.status_code == 200
            assert get_task_response.json()["task"]["task_id"] == task["task_id"]

            list_tasks_response = client.get(f"/api/v1/a2a/sessions/{session_id}/tasks")
            assert list_tasks_response.status_code == 200
            assert [item["task_id"] for item in list_tasks_response.json()["tasks"]] == [
                task["task_id"]
            ]
    finally:
        app_main.get_config.cache_clear()
