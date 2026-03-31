from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.api.dependencies import get_codex_bridge_client
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.jobs import JobRepository
from app.repositories.messages import MessageRepository
from app.repositories.rules import RuleRepository


class FakeBridge:
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
        return {"result": {"thread_id": str(payload.get("thread_id", "thr_1")), "resumed": True}}

    async def turn_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.turn_start_calls.append(payload)
        call_number = len(self.turn_start_calls)
        return {
            "result": {
                "turn_id": f"turn_{call_number}",
                "status": "running",
                "output_text": f"Rule output {call_number}",
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
    return f"sqlite:///{(tmp_path / 'rules.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _build_app(bridge: FakeBridge):
    app_main.get_config.cache_clear()
    app = app_main.create_app()
    app.dependency_overrides[get_codex_bridge_client] = lambda: bridge
    return app


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


def _add_participant(client: TestClient, *, session_id: str, agent_id: str) -> None:
    response = client.post(
        f"/api/v1/sessions/{session_id}/participants",
        json={"agent_id": agent_id},
    )
    assert response.status_code == 201


def test_rule_manual_activation_gates_jobs_until_deactivated(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    bridge = FakeBridge()
    app = _build_app(bridge)

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
                title="Rule gate",
                goal="Exercise manual activation",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(client, session_id=session_id, agent_id=builder_agent_id)

            heartbeat_response = client.post(
                f"/api/v1/agents/{builder_agent_id}/heartbeat",
                json={"presence": "online"},
            )
            assert heartbeat_response.status_code == 201

            create_rule_response = client.post(
                f"/api/v1/sessions/{session_id}/rules",
                json={
                    "rule_type": "review_required",
                    "name": "Manual review gate",
                    "description": "Hold jobs until activated",
                    "priority": 10,
                    "is_active": False,
                    "conditions": {"channel_key": "general"},
                    "actions": {"hold": True},
                },
            )
            assert create_rule_response.status_code == 201
            rule_body = create_rule_response.json()["rule"]
            assert rule_body["is_active"] is False

            list_rules_response = client.get(f"/api/v1/sessions/{session_id}/rules")
            assert list_rules_response.status_code == 200
            assert len(list_rules_response.json()["rules"]) == 1

            activate_response = client.post(
                f"/api/v1/sessions/{session_id}/rules/{rule_body['id']}/activate"
            )
            assert activate_response.status_code == 200
            assert activate_response.json()["rule"]["is_active"] is True

            active_rules_response = client.get(f"/api/v1/sessions/{session_id}/rules")
            assert active_rules_response.status_code == 200
            assert active_rules_response.json()["rules"][0]["is_active"] is True

            job_create_response = client.post(
                "/api/v1/jobs",
                json={
                    "session_id": session_id,
                    "assigned_agent_id": builder_agent_id,
                    "title": "Blocked job",
                    "instructions": "Wait for manual activation",
                    "channel_key": "general",
                    "priority": "normal",
                },
            )
            assert job_create_response.status_code == 201
            job_body = job_create_response.json()["job"]["job"]
            assert job_body["status"] == "input_required"
            assert job_body["last_known_turn_status"] == "review_required"
            assert bridge.turn_start_calls == []

            job_repository = JobRepository(database_url)
            stored_jobs = asyncio.run(job_repository.list_by_session(session_id))
            assert len(stored_jobs) == 1
            assert stored_jobs[0].status == "input_required"

            deactivate_response = client.post(
                f"/api/v1/sessions/{session_id}/rules/{rule_body['id']}/deactivate"
            )
            assert deactivate_response.status_code == 200
            assert deactivate_response.json()["rule"]["is_active"] is False

            resume_response = client.post(
                f"/api/v1/jobs/{job_body['id']}/resume",
                json={"reason": "manual activation completed"},
            )
            assert resume_response.status_code == 200
            resumed_job = resume_response.json()["job"]["job"]
            assert resumed_job["status"] == "running"
            assert len(bridge.turn_start_calls) == 1

            rule_repository = RuleRepository(database_url)
            active_rules = asyncio.run(rule_repository.list_active_by_session(session_id))
            assert active_rules == []
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()


def test_channel_routing_preference_moves_mentions_to_review_channel(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    bridge = FakeBridge()
    app = _build_app(bridge)

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
                title="Rule routing",
                goal="Exercise routing preference",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(client, session_id=session_id, agent_id=builder_agent_id)

            heartbeat_response = client.post(
                f"/api/v1/agents/{builder_agent_id}/heartbeat",
                json={"presence": "online"},
            )
            assert heartbeat_response.status_code == 201

            create_rule_response = client.post(
                f"/api/v1/sessions/{session_id}/rules",
                json={
                    "rule_type": "channel_routing_preference",
                    "name": "Route to review",
                    "description": "Send general mentions to review",
                    "priority": 5,
                    "is_active": True,
                    "conditions": {"channel_key": "general"},
                    "actions": {"target_channel_key": "review"},
                },
            )
            assert create_rule_response.status_code == 201
            assert create_rule_response.json()["rule"]["is_active"] is True

            message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": builder_agent_id,
                    "content": "#builder check the review lane",
                    "reply_to_message_id": None,
                    "channel_key": "general",
                },
            )
            assert message_response.status_code == 202
            payload = message_response.json()
            assert len(payload["routing"]["created_jobs"]) == 1
            assert len(bridge.turn_start_calls) == 1

            job_repository = JobRepository(database_url)
            jobs = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs) == 1
            assert jobs[0].channel_key == "review"

            message_repository = MessageRepository(database_url)
            messages = asyncio.run(message_repository.list_by_session_and_channel(session_id, "review"))
            assert [message.message_type for message in messages] == ["relay"]
            assert all(message.channel_key == "review" for message in messages)
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()
