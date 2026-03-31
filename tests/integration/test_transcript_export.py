from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRecord
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.messages import (
    MessageMentionRecord,
    MessageMentionRepository,
    MessageRecord,
    MessageRepository,
)
from app.repositories.session_events import SessionEventRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'transcript_export.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def test_session_transcript_export_and_artifact_listing(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            agent_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Builder",
                    "role": "builder",
                    "is_lead": True,
                    "runtime_kind": "codex",
                },
            )
            assert agent_response.status_code == 201
            agent_id = agent_response.json()["agent"]["id"]

            session_response = client.post(
                "/api/v1/sessions",
                json={
                    "title": "Transcript export",
                    "goal": "Produce an export bundle",
                    "lead_agent_id": agent_id,
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["session"]["id"]

            message_repository = MessageRepository(database_url)
            mention_repository = MessageMentionRepository(database_url)
            job_repository = JobRepository(database_url)
            artifact_repository = ArtifactRepository(database_url)
            session_event_repository = SessionEventRepository(database_url)

            asyncio.run(
                message_repository.create(
                    MessageRecord(
                        id="msg_export_001",
                        session_id=session_id,
                        sender_type="agent",
                        sender_id=agent_id,
                        message_type="chat",
                        content="Export this #builder transcript",
                        content_format="plain_text",
                        reply_to_message_id=None,
                        source_message_id=None,
                        visibility="session",
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:00:00Z",
                        channel_key="general",
                    )
                )
            )
            asyncio.run(
                mention_repository.create(
                    MessageMentionRecord(
                        id="mmt_export_001",
                        message_id="msg_export_001",
                        mentioned_agent_id=agent_id,
                        mention_text="#builder",
                        mention_order=0,
                        created_at="2026-03-31T00:00:00Z",
                    )
                )
            )
            asyncio.run(
                job_repository.create(
                    JobRecord(
                        id="job_export_001",
                        session_id=session_id,
                        assigned_agent_id=agent_id,
                        runtime_id=None,
                        source_message_id=None,
                        parent_job_id=None,
                        title="Export source",
                        instructions="Build the export bundle",
                        status="completed",
                        hop_count=0,
                        priority="normal",
                        codex_runtime_id=None,
                        codex_thread_id=None,
                        active_turn_id=None,
                        last_known_turn_status=None,
                        result_summary="Complete",
                        error_code=None,
                        error_message=None,
                        started_at="2026-03-31T00:00:00Z",
                        completed_at="2026-03-31T00:01:00Z",
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:01:00Z",
                        channel_key="general",
                    )
                )
            )
            asyncio.run(
                artifact_repository.create(
                    ArtifactRecord(
                        id="art_export_001",
                        job_id="job_export_001",
                        session_id=session_id,
                        source_message_id=None,
                        artifact_type="json",
                        title="Export artifact",
                        content_text='{"ok": true}',
                        file_path=None,
                        file_name="export.json",
                        mime_type="application/json",
                        size_bytes=12,
                        checksum_sha256="checksum-export",
                        metadata_json='{"kind":"export"}',
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:00:00Z",
                        channel_key="general",
                    )
                )
            )

            export_response = client.post(f"/api/v1/sessions/{session_id}/transcript-export")
            assert export_response.status_code == 201
            export_payload = export_response.json()["transcript_export"]
            assert export_payload["mime_type"] == "application/json"
            assert export_payload["file_name"].endswith(".json")
            assert export_payload["metadata"]["message_count"] == 1
            assert export_payload["metadata"]["job_count"] == 1
            assert export_payload["metadata"]["artifact_count"] == 1
            assert export_payload["content_text"].startswith("{")

            session_artifacts_response = client.get(
                f"/api/v1/sessions/{session_id}/artifacts"
            )
            assert session_artifacts_response.status_code == 200
            session_artifacts = session_artifacts_response.json()
            assert len(session_artifacts["artifacts"]) == 1
            assert len(session_artifacts["transcript_exports"]) == 1
            assert session_artifacts["transcript_exports"][0]["id"] == export_payload["id"]

            detail_response = client.get(
                f"/api/v1/transcript-exports/{export_payload['id']}"
            )
            assert detail_response.status_code == 200
            assert detail_response.json()["transcript_export"]["id"] == export_payload["id"]

            events = asyncio.run(session_event_repository.list_by_session(session_id))
            assert any(event.event_type == "transcript.exported" for event in events)
    finally:
        app_main.get_config.cache_clear()
