from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.api.dependencies import get_codex_bridge_client, get_thread_mapping_store
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.participants import ParticipantRepository, SessionParticipantRecord
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository


class FakeBridge:
    """Deterministic bridge for F15 integration tests."""

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
                "output_text": f"Bridge output {call_number}",
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


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'f15.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _build_app(database_url: str, bridge: FakeBridge):
    app_main.get_config.cache_clear()
    get_thread_mapping_store().clear()
    app = app_main.create_app()
    app.dependency_overrides[get_codex_bridge_client] = lambda: bridge
    return app


def _seed_agent(
    database_url: str,
    *,
    agent_id: str,
    display_name: str,
    role: str,
    is_lead: bool,
    runtime_id: str,
    runtime_status: str = "online",
) -> None:
    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    created_at = "2026-03-31T00:00:00Z"
    asyncio.run(
        agent_repository.create(
            AgentRecord(
                id=agent_id,
                display_name=display_name,
                role=role,
                is_lead_default=int(is_lead),
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )
    asyncio.run(
        runtime_repository.create(
            AgentRuntimeRecord(
                id=runtime_id,
                agent_id=agent_id,
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status=runtime_status,
                last_heartbeat_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    )


def _seed_session(database_url: str, *, session_id: str, lead_agent_id: str) -> None:
    session_repository = SessionRepository(database_url)
    asyncio.run(
        session_repository.create(
            SessionRecord(
                id=session_id,
                title="F15 session",
                goal="Exercise presence and streaming",
                status="active",
                lead_agent_id=lead_agent_id,
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )


def _seed_participant(database_url: str, *, session_id: str, agent_id: str, is_lead: int) -> None:
    participant_repository = ParticipantRepository(database_url)
    asyncio.run(
        participant_repository.create(
            SessionParticipantRecord(
                id=f"sp_{session_id}_{agent_id}",
                session_id=session_id,
                agent_id=agent_id,
                runtime_id=None,
                is_lead=is_lead,
                read_scope="shared_history",
                write_scope="mention_or_direct_assignment",
                participant_status="joined",
                joined_at="2026-03-31T00:00:00Z",
                left_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )


def _seed_running_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    thread_id: str,
    turn_id: str,
) -> None:
    job_repository = JobRepository(database_url)
    asyncio.run(
        job_repository.create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                assigned_agent_id=agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Recovered job",
                instructions="Continue the previous work",
                status="running",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=thread_id,
                active_turn_id=turn_id,
                last_known_turn_status="running",
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at="2026-03-31T00:00:00Z",
                completed_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )


def _seed_input_required_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    thread_id: str,
    turn_id: str,
) -> None:
    job_repository = JobRepository(database_url)
    asyncio.run(
        job_repository.create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                assigned_agent_id=agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Need human input",
                instructions="Awaiting input",
                status="input_required",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=thread_id,
                active_turn_id=turn_id,
                last_known_turn_status="input_required",
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at="2026-03-31T00:00:00Z",
                completed_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )


def _seed_approval(
    database_url: str,
    *,
    approval_id: str,
    job_id: str,
    agent_id: str,
) -> None:
    approval_repository = ApprovalRepository(database_url)
    asyncio.run(
        approval_repository.create(
            ApprovalRequestRecord(
                id=approval_id,
                job_id=job_id,
                agent_id=agent_id,
                approval_type="custom",
                status="pending",
                request_payload_json='{"prompt":"approve"}',
                decision_payload_json=None,
                requested_at="2026-03-31T00:00:00Z",
                resolved_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )


def test_presence_job_surface_streaming_and_input(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    bridge = FakeBridge()
    app = _build_app(database_url, bridge)

    try:
        with TestClient(app) as client:
            lead_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Lead",
                    "role": "planner",
                    "is_lead": True,
                    "runtime_kind": "codex",
                },
            )
            builder_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Builder",
                    "role": "builder",
                    "is_lead": False,
                    "runtime_kind": "codex",
                },
            )
            assert lead_response.status_code == 201
            assert builder_response.status_code == 201
            lead_id = lead_response.json()["agent"]["id"]
            builder_id = builder_response.json()["agent"]["id"]

            session_response = client.post(
                "/api/v1/sessions",
                json={
                    "title": "F15",
                    "goal": "Surface APIs",
                    "lead_agent_id": lead_id,
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["session"]["id"]

            heartbeat_response = client.post(
                f"/api/v1/agents/{builder_id}/heartbeat",
                json={
                    "presence": "busy",
                    "details": {"pid": 1234},
                },
            )
            assert heartbeat_response.status_code == 201
            assert heartbeat_response.json()["presence"]["presence"] == "busy"
            presence_response = client.get(f"/api/v1/agents/{builder_id}/presence")
            assert presence_response.status_code == 200
            assert presence_response.json()["presence"]["presence"] == "busy"

            participant_response = client.post(
                f"/api/v1/sessions/{session_id}/participants",
                json={"agent_id": builder_id},
            )
            assert participant_response.status_code == 201

            message_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": builder_id,
                    "content": "#builder fix this bug",
                    "reply_to_message_id": None,
                },
            )
            assert message_response.status_code == 202
            job_id = message_response.json()["routing"]["created_jobs"][0]

            job_response = client.get(f"/api/v1/jobs/{job_id}")
            assert job_response.status_code == 200
            job_detail = job_response.json()["job"]
            assert job_detail["job"]["id"] == job_id
            assert job_detail["artifacts"][0]["artifact_type"] == "final_text"
            assert {event["event_type"] for event in job_detail["events"]} >= {
                "turn.started",
                "relay.output.published",
                "artifact.created",
            }

            events_response = client.get(f"/api/v1/jobs/{job_id}/events")
            artifacts_response = client.get(f"/api/v1/jobs/{job_id}/artifacts")
            job_stream_response = client.get(f"/api/v1/jobs/{job_id}/stream")
            session_stream_response = client.get(f"/api/v1/sessions/{session_id}/stream")
            assert events_response.status_code == 200
            assert artifacts_response.status_code == 200
            assert job_stream_response.status_code == 200
            assert session_stream_response.status_code == 200
            assert job_stream_response.headers["content-type"].startswith("text/event-stream")
            assert session_stream_response.headers["content-type"].startswith("text/event-stream")
            assert "event: job" in job_stream_response.text
            assert "event: artifact" in job_stream_response.text
            assert "event: session" in session_stream_response.text
            assert "event: message" in session_stream_response.text

            input_job_id = "job_input_001"
            _seed_input_required_job(
                database_url,
                job_id=input_job_id,
                session_id=session_id,
                agent_id=builder_id,
                thread_id="thr_seed",
                turn_id="turn_seed",
            )
            input_response = client.post(
                f"/api/v1/jobs/{input_job_id}/input",
                json={"input_text": "Continue from here"},
            )
            assert input_response.status_code == 200
            assert input_response.json()["job"]["job"]["status"] == "running"
            assert len(bridge.thread_resume_calls) == 1
            assert len(bridge.turn_start_calls) == 2
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        get_thread_mapping_store().clear()
        app_main.get_config.cache_clear()


def test_loop_guard_pauses_third_relay(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    bridge = FakeBridge()
    app = _build_app(database_url, bridge)

    try:
        with TestClient(app) as client:
            lead_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Lead",
                    "role": "planner",
                    "is_lead": True,
                    "runtime_kind": "codex",
                },
            )
            builder_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Builder",
                    "role": "builder",
                    "is_lead": False,
                    "runtime_kind": "codex",
                },
            )
            assert lead_response.status_code == 201
            assert builder_response.status_code == 201
            lead_id = lead_response.json()["agent"]["id"]
            builder_id = builder_response.json()["agent"]["id"]

            session_response = client.post(
                "/api/v1/sessions",
                json={
                    "title": "Loop guard",
                    "goal": "Pause loops",
                    "lead_agent_id": lead_id,
                },
            )
            session_id = session_response.json()["session"]["id"]
            client.post(
                f"/api/v1/sessions/{session_id}/participants",
                json={"agent_id": builder_id},
            )

            for index in range(3):
                response = client.post(
                    f"/api/v1/sessions/{session_id}/messages",
                    json={
                        "sender_type": "agent",
                        "sender_id": builder_id,
                        "content": f"#builder pass {index}",
                        "reply_to_message_id": None,
                    },
                )
                assert response.status_code == 202

            job_repository = JobRepository(database_url)
            jobs = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs) == 3
            assert jobs[-1].status == "paused_by_loop_guard"
            assert len(bridge.turn_start_calls) == 2

            event_repository = SessionEventRepository(database_url)
            events = asyncio.run(event_repository.list_by_session(session_id))
            assert any(event.event_type == "loop_guard_triggered" for event in events)
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        get_thread_mapping_store().clear()
        app_main.get_config.cache_clear()


def test_recovery_rehydrates_thread_mapping_on_startup(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    get_thread_mapping_store().clear()

    _seed_agent(
        database_url,
        agent_id="agt_builder",
        display_name="Builder",
        role="builder",
        is_lead=False,
        runtime_id="rt_builder",
    )
    _seed_session(database_url, session_id="ses_recover", lead_agent_id="agt_builder")
    _seed_participant(database_url, session_id="ses_recover", agent_id="agt_builder", is_lead=0)
    _seed_running_job(
        database_url,
        job_id="job_recover",
        session_id="ses_recover",
        agent_id="agt_builder",
        thread_id="thr_seed",
        turn_id="turn_seed",
    )

    bridge = FakeBridge()
    app = _build_app(database_url, bridge)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/sessions/ses_recover/messages",
                json={
                    "sender_type": "agent",
                    "sender_id": "agt_builder",
                    "content": "#builder recover this",
                    "reply_to_message_id": None,
                },
            )
            assert response.status_code == 202
            assert len(bridge.thread_start_calls) == 0
            assert len(bridge.thread_resume_calls) == 1
            assert bridge.thread_resume_calls[0]["thread_id"] == "thr_seed"

            event_repository = SessionEventRepository(database_url)
            events = asyncio.run(event_repository.list_by_session("ses_recover"))
            assert any(event.event_type == "recovery.thread_rehydrated" for event in events)
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        get_thread_mapping_store().clear()
        app_main.get_config.cache_clear()


def test_approval_accept_and_decline_endpoints(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    bridge = FakeBridge()
    app = _build_app(database_url, bridge)

    try:
        with TestClient(app) as client:
            lead_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Lead",
                    "role": "planner",
                    "is_lead": True,
                    "runtime_kind": "codex",
                },
            )
            builder_response = client.post(
                "/api/v1/agents",
                json={
                    "display_name": "Builder",
                    "role": "builder",
                    "is_lead": False,
                    "runtime_kind": "codex",
                },
            )
            lead_id = lead_response.json()["agent"]["id"]
            builder_id = builder_response.json()["agent"]["id"]
            session_response = client.post(
                "/api/v1/sessions",
                json={
                    "title": "Approval flow",
                    "goal": "Test approvals",
                    "lead_agent_id": lead_id,
                },
            )
            session_id = session_response.json()["session"]["id"]
            client.post(
                f"/api/v1/sessions/{session_id}/participants",
                json={"agent_id": builder_id},
            )

            approval_job_id = "job_approval_accept"
            decline_job_id = "job_approval_decline"
            job_repository = JobRepository(database_url)
            asyncio.run(
                job_repository.create(
                    JobRecord(
                        id=approval_job_id,
                        session_id=session_id,
                        assigned_agent_id=builder_id,
                        runtime_id=None,
                        source_message_id=None,
                        parent_job_id=None,
                        title="Need approval",
                        instructions="Wait for approval",
                        status="input_required",
                        hop_count=0,
                        priority="normal",
                        codex_runtime_id=None,
                        codex_thread_id="thr_approval",
                        active_turn_id="turn_approval",
                        last_known_turn_status="input_required",
                        result_summary=None,
                        error_code=None,
                        error_message=None,
                        started_at="2026-03-31T00:00:00Z",
                        completed_at=None,
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:00:00Z",
                    )
                )
            )
            asyncio.run(
                job_repository.create(
                    JobRecord(
                        id=decline_job_id,
                        session_id=session_id,
                        assigned_agent_id=builder_id,
                        runtime_id=None,
                        source_message_id=None,
                        parent_job_id=None,
                        title="Need decline",
                        instructions="Wait for decline",
                        status="input_required",
                        hop_count=0,
                        priority="normal",
                        codex_runtime_id=None,
                        codex_thread_id="thr_decline",
                        active_turn_id="turn_decline",
                        last_known_turn_status="input_required",
                        result_summary=None,
                        error_code=None,
                        error_message=None,
                        started_at="2026-03-31T00:00:00Z",
                        completed_at=None,
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:00:00Z",
                    )
                )
            )
            approval_repository = ApprovalRepository(database_url)
            asyncio.run(
                approval_repository.create(
                    ApprovalRequestRecord(
                        id="apr_accept",
                        job_id=approval_job_id,
                        agent_id=builder_id,
                        approval_type="custom",
                        status="pending",
                        request_payload_json='{"prompt":"approve"}',
                        decision_payload_json=None,
                        requested_at="2026-03-31T00:00:00Z",
                        resolved_at=None,
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:00:00Z",
                    )
                )
            )
            asyncio.run(
                approval_repository.create(
                    ApprovalRequestRecord(
                        id="apr_decline",
                        job_id=decline_job_id,
                        agent_id=builder_id,
                        approval_type="custom",
                        status="pending",
                        request_payload_json='{"prompt":"decline"}',
                        decision_payload_json=None,
                        requested_at="2026-03-31T00:00:00Z",
                        resolved_at=None,
                        created_at="2026-03-31T00:00:00Z",
                        updated_at="2026-03-31T00:00:00Z",
                    )
                )
            )

            accept_response = client.post(
                "/api/v1/approvals/apr_accept/accept",
                json={"decision_payload": {"approved_by": "lead"}},
            )
            decline_response = client.post(
                "/api/v1/approvals/apr_decline/decline",
                json={"decision_payload": {"declined_by": "lead"}},
            )
            assert accept_response.status_code == 200
            assert decline_response.status_code == 200
            assert accept_response.json()["status"] == "accepted"
            assert decline_response.json()["status"] == "declined"

            refreshed_jobs = asyncio.run(job_repository.list_by_session(session_id))
            status_by_id = {job.id: job.status for job in refreshed_jobs}
            assert status_by_id[approval_job_id] == "queued"
            assert status_by_id[decline_job_id] == "canceled"
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        get_thread_mapping_store().clear()
        app_main.get_config.cache_clear()
