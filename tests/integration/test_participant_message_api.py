from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.api.dependencies import get_codex_bridge_client
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.artifacts import ArtifactRepository
from app.repositories.jobs import JobEventRepository, JobRepository
from app.repositories.messages import MessageMentionRepository, MessageRepository
from app.repositories.relay_edges import RelayEdgeRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository


class FakeBridge:
    """Deterministic bridge for relay and command integration tests."""

    def __init__(self) -> None:
        self.thread_start_calls: list[dict[str, object]] = []
        self.thread_resume_calls: list[dict[str, object]] = []
        self.turn_start_calls: list[dict[str, object]] = []
        self.turn_interrupt_calls: list[dict[str, object]] = []
        self.thread_compact_start_calls: list[dict[str, object]] = []

    async def thread_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.thread_start_calls.append(payload)
        return {"result": {"thread_id": f"thr_{len(self.thread_start_calls)}"}}

    async def thread_resume(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.thread_resume_calls.append(payload)
        thread_id = str(payload.get("thread_id", "thr_1"))
        return {"result": {"thread_id": thread_id, "resumed": True}}

    async def turn_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.turn_start_calls.append(payload)
        call_number = len(self.turn_start_calls)
        return {
            "result": {
                "turn_id": f"turn_{call_number}",
                "status": "running",
                "output_text": f"Relay output {call_number}",
            }
        }

    async def turn_interrupt(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.turn_interrupt_calls.append(payload)
        return {"result": {"turn_id": payload.get("turn_id"), "interrupted": True}}

    async def thread_compact_start(
        self, params: dict[str, object] | None = None
    ) -> dict[str, object]:
        payload = dict(params or {})
        self.thread_compact_start_calls.append(payload)
        return {
            "result": {
                "thread_id": payload.get("thread_id"),
                "compacted": True,
                "summary": "Compact summary",
            }
        }


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'participant_message_api.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _install_bridge_override(app, bridge: FakeBridge) -> None:
    app.dependency_overrides[get_codex_bridge_client] = lambda: bridge


def test_participant_and_message_api_log_session_events(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()
    fake_bridge = FakeBridge()
    _install_bridge_override(app, fake_bridge)

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

            channels_response = client.get(f"/api/v1/sessions/{session_id}/channels")
            assert channels_response.status_code == 200
            assert [channel["channel_key"] for channel in channels_response.json()["channels"]] == [
                "general",
                "planning",
                "review",
                "debug",
            ]

            create_channel_response = client.post(
                f"/api/v1/sessions/{session_id}/channels",
                json={
                    "channel_key": "research",
                    "display_name": "Research",
                    "description": "Research notes",
                },
            )
            assert create_channel_response.status_code == 201
            assert create_channel_response.json()["channel"]["channel_key"] == "research"

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
            assert participant_body["agent_role"] == "builder"
            assert participant_body["role"] == "builder"
            assert participant_body["is_lead"] is False
            assert participant_body["read_scope"] == "shared_history"
            assert participant_body["policy"]["can_relay"] is True
            assert participant_body["policy"]["can_target_other_agents"] is False

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
                    "channel_key": "research",
                },
            )
            assert create_message_response.status_code == 202
            message_envelope = create_message_response.json()
            message_body = message_envelope["message"]
            message_id = message_body["id"]
            assert message_body["session_id"] == session_id
            assert message_body["channel_key"] == "research"
            assert message_body["sender_id"] == builder_agent_id
            assert message_body["message_type"] == "chat"
            assert message_body["mentions"] == [builder_agent_id]
            assert message_envelope["routing"]["detected_mentions"] == [builder_agent_id]
            assert len(message_envelope["routing"]["created_jobs"]) == 1

            mention_repository = MessageMentionRepository(database_url)
            message_repository = MessageRepository(database_url)
            job_event_repository = JobEventRepository(database_url)
            relay_edge_repository = RelayEdgeRepository(database_url)
            mentions = asyncio.run(mention_repository.list_by_message(message_id))
            assert len(mentions) == 1
            assert mentions[0].mentioned_agent_id == builder_agent_id
            assert mentions[0].mention_text == "#builder"

            job_repository = JobRepository(database_url)
            jobs = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs) == 1
            assert jobs[0].channel_key == "research"
            assert jobs[0].assigned_agent_id == builder_agent_id
            assert jobs[0].source_message_id == message_id
            assert jobs[0].status == "running"
            assert jobs[0].codex_thread_id == "thr_1"
            assert jobs[0].active_turn_id == "turn_1"

            artifact_repository = ArtifactRepository(database_url)
            artifacts = asyncio.run(artifact_repository.list_by_job(jobs[0].id))
            assert artifacts[0].channel_key == "research"

            session_messages = asyncio.run(message_repository.list_by_session(session_id))
            assert len(session_messages) == 2
            assert session_messages[0].id == message_id
            assert session_messages[0].channel_key == "research"
            assert session_messages[1].sender_type == "agent"
            assert session_messages[1].channel_key == "research"
            assert session_messages[1].message_type == "relay"
            assert session_messages[1].content == "Relay output 1"

            job_events = asyncio.run(job_event_repository.list_by_session(session_id))
            assert {event.event_type for event in job_events} == {
                "turn.started",
                "relay.output.published",
                "artifact.created",
            }
            relay_edges = asyncio.run(relay_edge_repository.list_by_session(session_id))
            assert len(relay_edges) == 1
            assert relay_edges[0].relay_reason == "mention"

            command_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": builder_agent_id,
                    "content": "/interrupt #builder",
                    "reply_to_message_id": None,
                    "channel_key": "research",
                },
            )
            assert command_message_response.status_code == 202
            command_envelope = command_message_response.json()
            assert command_envelope["message"]["message_type"] == "command"
            assert command_envelope["routing"]["detected_mentions"] == []
            assert command_envelope["routing"]["created_jobs"] == []
            jobs_after_command = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs_after_command) == 1
            assert jobs_after_command[0].status == "canceled"
            assert jobs_after_command[0].last_known_turn_status == "interrupted"

            compact_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": builder_agent_id,
                    "content": "/compact #builder",
                    "reply_to_message_id": None,
                    "channel_key": "research",
                },
            )
            assert compact_message_response.status_code == 202
            compact_envelope = compact_message_response.json()
            assert compact_envelope["message"]["message_type"] == "command"
            assert compact_envelope["routing"]["created_jobs"] == []

            new_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "user",
                    "sender_id": "usr_local",
                    "content": "/new #builder continue from here",
                    "reply_to_message_id": None,
                    "channel_key": "research",
                },
            )
            assert new_message_response.status_code == 202
            new_envelope = new_message_response.json()
            assert new_envelope["message"]["message_type"] == "command"
            assert new_envelope["routing"]["created_jobs"] == []

            jobs_after_new = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs_after_new) == 2
            assert jobs_after_new[-1].status == "running"
            assert jobs_after_new[-1].channel_key == "research"
            assert jobs_after_new[-1].codex_thread_id == "thr_1"
            assert jobs_after_new[-1].active_turn_id == "turn_2"

            session_messages_after = asyncio.run(message_repository.list_by_session(session_id))
            assert len(session_messages_after) == 6
            assert all(message.channel_key == "research" for message in session_messages_after)
            assert session_messages_after[-1].message_type == "relay"
            assert session_messages_after[-1].content == "Relay output 2"

            job_events_after = asyncio.run(job_event_repository.list_by_session(session_id))
            assert {event.event_type for event in job_events_after} == {
                "turn.started",
                "relay.output.published",
                "turn.interrupted",
                "thread.compact.start",
                "artifact.created",
            }
            assert sum(event.event_type == "turn.started" for event in job_events_after) == 2

            relay_edges_after = asyncio.run(relay_edge_repository.list_by_session(session_id))
            assert len(relay_edges_after) == 2
            assert {edge.relay_reason for edge in relay_edges_after} == {
                "mention",
                "manual_relay",
            }

            reviewer_participant_response = client.post(
                f"/api/v1/sessions/{session_id}/participants",
                json={
                    "agent_id": rogue_agent_id,
                    "role": "reviewer",
                },
            )
            assert reviewer_participant_response.status_code == 201
            reviewer_participant = reviewer_participant_response.json()["participant"]
            assert reviewer_participant["role"] == "reviewer"
            assert reviewer_participant["agent_role"] == "reviewer"
            assert reviewer_participant["policy"]["can_relay"] is False
            assert reviewer_participant["policy"]["review_only_actions"] is True

            reviewer_blocked_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": rogue_agent_id,
                    "content": "#builder please review this",
                    "reply_to_message_id": None,
                    "channel_key": "research",
                },
            )
            assert reviewer_blocked_response.status_code == 403

            reviewer_patch_response = client.patch(
                f"/api/v1/sessions/{session_id}/participants/{rogue_agent_id}",
                json={
                    "policy": {
                        "can_relay": True,
                        "can_target_other_agents": True,
                    }
                },
            )
            assert reviewer_patch_response.status_code == 200
            reviewer_patched = reviewer_patch_response.json()["participant"]
            assert reviewer_patched["role"] == "reviewer"
            assert reviewer_patched["policy"]["can_relay"] is True
            assert reviewer_patched["policy"]["can_target_other_agents"] is True
            assert reviewer_patched["policy"]["can_create_job"] is False

            reviewer_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": rogue_agent_id,
                    "content": "#builder please review this",
                    "reply_to_message_id": None,
                    "channel_key": "research",
                },
            )
            assert reviewer_message_response.status_code == 202
            reviewer_message_envelope = reviewer_message_response.json()
            assert len(reviewer_message_envelope["routing"]["created_jobs"]) == 1

            get_message_response = client.get(f"/api/v1/messages/{message_id}")
            assert get_message_response.status_code == 200
            assert get_message_response.json()["message"]["content"] == "#builder fix this bug"

            general_message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "user",
                    "sender_id": "usr_local",
                    "content": "General note",
                    "reply_to_message_id": None,
                },
            )
            assert general_message_response.status_code == 202
            assert general_message_response.json()["message"]["channel_key"] == "general"

            filtered_messages_response = client.get(
                f"/api/v1/sessions/{session_id}/messages",
                params={"channel_key": "research"},
            )
            assert filtered_messages_response.status_code == 200
            filtered_messages = filtered_messages_response.json()["messages"]
            assert len(filtered_messages) == 7
            assert all(message["channel_key"] == "research" for message in filtered_messages)

            list_messages_response = client.get(f"/api/v1/sessions/{session_id}/messages")
            assert list_messages_response.status_code == 200
            assert list_messages_response.json()["messages"][0]["id"] == message_id

            delete_reviewer_response = client.delete(
                f"/api/v1/sessions/{session_id}/participants/{rogue_agent_id}"
            )
            assert delete_reviewer_response.status_code == 204

            delete_participant_response = client.delete(
                f"/api/v1/sessions/{session_id}/participants/{builder_agent_id}"
            )
            assert delete_participant_response.status_code == 204

            list_after_delete_response = client.get(f"/api/v1/sessions/{session_id}/participants")
            assert list_after_delete_response.status_code == 200
            assert list_after_delete_response.json()["participants"] == []

            event_repository = SessionEventRepository(database_url)
            events = asyncio.run(event_repository.list_by_session(session_id))
            assert {event.event_type for event in events} == {
                "participant.added",
                "participant.updated",
                "message.created",
                "relay.output.published",
                "command.interrupt",
                "command.compact",
                "command.new",
                "loop_guard_triggered",
                "participant.removed",
            }
            assert sum(event.event_type == "message.created" for event in events) == 8

            session_repository = SessionRepository(database_url)
            stored_session = asyncio.run(session_repository.get(session_id))
            assert stored_session is not None
            assert (
                stored_session.last_message_at
                == general_message_response.json()["message"]["created_at"]
            )
            assert len(fake_bridge.thread_start_calls) == 1
            assert len(fake_bridge.thread_resume_calls) == 1
            assert len(fake_bridge.turn_start_calls) == 2
            assert len(fake_bridge.turn_interrupt_calls) == 1
            assert len(fake_bridge.thread_compact_start_calls) == 1
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()
