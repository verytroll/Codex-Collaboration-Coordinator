from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.jobs import JobRepository
from app.repositories.messages import MessageMentionRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'participant_message_api.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def test_participant_and_message_api_log_session_events(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Lead",
                    "role": "planner",
                    "is_lead": True,
                    "runtime_kind": "codex",
                    "runtime_config": {
                        "workspace_path": "/workspace/project",
                        "sandbox_mode": "workspace-write",
                    },
                },
            )
            assert lead_agent_response.status_code == 201
            lead_agent_id = lead_agent_response.json()["agent"]["id"]

            builder_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Builder",
                    "role": "builder",
                    "is_lead": False,
                    "runtime_kind": "codex",
                    "runtime_config": {
                        "workspace_path": "/workspace/project",
                        "sandbox_mode": "workspace-write",
                    },
                },
            )
            assert builder_response.status_code == 201
            builder_agent_id = builder_response.json()["agent"]["id"]

            rogue_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Rogue",
                    "role": "reviewer",
                    "is_lead": False,
                    "runtime_kind": "codex",
                },
            )
            assert rogue_response.status_code == 201
            rogue_agent_id = rogue_response.json()["agent"]["id"]

            session_response = client.post(
                "/api/v1/sessions",
                json={
                    "title": "Participant and message flow",
                    "goal": "Verify basic chat flow",
                    "lead_agent_id": lead_agent_id,
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["session"]["id"]

            forbidden_message = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": rogue_agent_id,
                    "content": "I should not be able to post yet",
                    "reply_to_message_id": None,
                },
            )
            assert forbidden_message.status_code == 403

            add_participant_response = client.post(
                f"/api/v1/sessions/{session_id}/participants",
                json={"agent_id": builder_agent_id},
            )
            assert add_participant_response.status_code == 201
            participant_body = add_participant_response.json()["participant"]
            assert participant_body["session_id"] == session_id
            assert participant_body["agent_id"] == builder_agent_id
            assert participant_body["read_scope"] == "shared_history"

            list_participants_response = client.get(f"/api/v1/sessions/{session_id}/participants")
            assert list_participants_response.status_code == 200
            assert list_participants_response.json()["participants"] == [participant_body]

            create_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": builder_agent_id,
                    "content": "#builder fix this bug",
                    "reply_to_message_id": None,
                },
            )
            assert create_message_response.status_code == 202
            message_envelope = create_message_response.json()
            message_body = message_envelope["message"]
            message_id = message_body["id"]
            assert message_body["session_id"] == session_id
            assert message_body["sender_id"] == builder_agent_id
            assert message_body["message_type"] == "chat"
            assert message_body["mentions"] == [builder_agent_id]
            assert message_envelope["routing"]["detected_mentions"] == [builder_agent_id]
            assert len(message_envelope["routing"]["created_jobs"]) == 1

            mention_repository = MessageMentionRepository(database_url)
            mentions = asyncio.run(mention_repository.list_by_message(message_id))
            assert len(mentions) == 1
            assert mentions[0].mentioned_agent_id == builder_agent_id
            assert mentions[0].mention_text == "#builder"

            job_repository = JobRepository(database_url)
            jobs = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs) == 1
            assert jobs[0].assigned_agent_id == builder_agent_id
            assert jobs[0].source_message_id == message_id
            assert jobs[0].status == "queued"

            command_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": builder_agent_id,
                    "content": "/interrupt #builder",
                    "reply_to_message_id": None,
                },
            )
            assert command_message_response.status_code == 202
            command_envelope = command_message_response.json()
            assert command_envelope["message"]["message_type"] == "command"
            assert command_envelope["routing"]["detected_mentions"] == []
            assert command_envelope["routing"]["created_jobs"] == []
            jobs_after_command = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs_after_command) == 1

            get_message_response = client.get(f"/api/v1/messages/{message_id}")
            assert get_message_response.status_code == 200
            assert get_message_response.json()["message"]["content"] == "#builder fix this bug"

            list_messages_response = client.get(f"/api/v1/sessions/{session_id}/messages")
            assert list_messages_response.status_code == 200
            assert list_messages_response.json()["messages"][0]["id"] == message_id

            delete_participant_response = client.delete(
                f"/api/v1/sessions/{session_id}/participants/{builder_agent_id}"
            )
            assert delete_participant_response.status_code == 204

            list_after_delete_response = client.get(f"/api/v1/sessions/{session_id}/participants")
            assert list_after_delete_response.status_code == 200
            assert list_after_delete_response.json()["participants"] == []

            event_repository = SessionEventRepository(database_url)
            events = asyncio.run(event_repository.list_by_session(session_id))
            assert len(events) == 4
            assert {event.event_type for event in events} == {
                "participant.added",
                "message.created",
                "participant.removed",
            }
            assert sum(event.event_type == "message.created" for event in events) == 2

            session_repository = SessionRepository(database_url)
            stored_session = asyncio.run(session_repository.get(session_id))
            assert stored_session is not None
            assert stored_session.last_message_at == command_envelope["message"]["created_at"]
    finally:
        app_main.get_config.cache_clear()
