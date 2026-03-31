from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.api.dependencies import get_codex_bridge_client
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.job_inputs import JobInputRepository
from app.repositories.jobs import JobRecord, JobRepository


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


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'jobs_v2.db').as_posix()}"


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


def test_direct_job_create_lists_and_queues_until_online(tmp_path, monkeypatch) -> None:
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
                title="Job queue",
                goal="Exercise direct job queueing",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(client, session_id=session_id, agent_id=builder_agent_id)

            offline_response = client.post(
                f"/api/v1/agents/{builder_agent_id}/heartbeat",
                json={"presence": "offline"},
            )
            assert offline_response.status_code == 201

            create_response = client.post(
                "/api/v1/jobs",
                json={
                    "session_id": session_id,
                    "assigned_agent_id": builder_agent_id,
                    "title": "Queued work",
                    "instructions": "Run this when online",
                    "channel_key": "general",
                    "priority": "normal",
                },
            )
            assert create_response.status_code == 201
            job_body = create_response.json()["job"]["job"]
            assert job_body["status"] == "queued"
            assert job_body["channel_key"] == "general"
            assert len(create_response.json()["job"]["inputs"]) == 1
            assert create_response.json()["job"]["inputs"][0]["input_type"] == "create"
            assert bridge.turn_start_calls == []

            job_repository = JobRepository(database_url)
            jobs = asyncio.run(job_repository.list_by_session(session_id))
            assert len(jobs) == 1
            assert jobs[0].status == "queued"

            list_response = client.get("/api/v1/jobs", params={"session_id": session_id})
            assert list_response.status_code == 200
            assert len(list_response.json()["jobs"]) == 1

            online_response = client.post(
                f"/api/v1/agents/{builder_agent_id}/heartbeat",
                json={"presence": "online"},
            )
            assert online_response.status_code == 201

            refreshed_jobs = asyncio.run(job_repository.list_by_session(session_id))
            assert refreshed_jobs[0].status == "running"
            assert len(bridge.turn_start_calls) == 1

            job_input_repository = JobInputRepository(database_url)
            inputs = asyncio.run(job_input_repository.list_by_job(refreshed_jobs[0].id))
            assert [job_input.input_type for job_input in inputs] == ["create"]
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()


def test_retry_route_requeues_failed_job(tmp_path, monkeypatch) -> None:
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
                title="Retry job",
                goal="Exercise retry",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(client, session_id=session_id, agent_id=builder_agent_id)

            job_repository = JobRepository(database_url)
            job = JobRecord(
                id="job_retry",
                session_id=session_id,
                assigned_agent_id=builder_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Retry me",
                instructions="This job failed",
                status="failed",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=None,
                active_turn_id=None,
                last_known_turn_status="failed",
                result_summary=None,
                error_code="boom",
                error_message="Failed once",
                started_at="2026-03-31T00:00:00Z",
                completed_at="2026-03-31T00:01:00Z",
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:01:00Z",
            )
            asyncio.run(job_repository.create(job))

            retry_response = client.post(
                f"/api/v1/jobs/{job.id}/retry",
                json={"reason": "manual retry"},
            )
            assert retry_response.status_code == 200
            retry_job = retry_response.json()["job"]["job"]
            assert retry_job["status"] == "running"
            assert len(bridge.turn_start_calls) == 1

            job_input_repository = JobInputRepository(database_url)
            inputs = asyncio.run(job_input_repository.list_by_job(job.id))
            assert [job_input.input_type for job_input in inputs] == ["retry"]
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()


def test_resume_route_rehydrates_blocked_job(tmp_path, monkeypatch) -> None:
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
                title="Resume job",
                goal="Exercise resume",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(client, session_id=session_id, agent_id=builder_agent_id)

            warmup_response = client.post(
                "/api/v1/jobs",
                json={
                    "session_id": session_id,
                    "assigned_agent_id": builder_agent_id,
                    "title": "Warmup",
                    "instructions": "Create mapping first",
                    "channel_key": "general",
                },
            )
            assert warmup_response.status_code == 201

            job_repository = JobRepository(database_url)
            job = JobRecord(
                id="job_resume",
                session_id=session_id,
                assigned_agent_id=builder_agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title="Resume me",
                instructions="Need a resume",
                status="input_required",
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id="thr_seed",
                active_turn_id="turn_seed",
                last_known_turn_status="input_required",
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at="2026-03-31T00:00:00Z",
                completed_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:01:00Z",
            )
            asyncio.run(job_repository.create(job))

            resume_response = client.post(
                f"/api/v1/jobs/{job.id}/resume",
                json={"reason": "manual resume"},
            )
            assert resume_response.status_code == 200
            resumed_job = resume_response.json()["job"]["job"]
            assert resumed_job["status"] == "running"
            assert len(bridge.thread_start_calls) == 1
            assert len(bridge.thread_resume_calls) == 1
            assert len(bridge.turn_start_calls) == 2

            job_input_repository = JobInputRepository(database_url)
            inputs = asyncio.run(job_input_repository.list_by_job(job.id))
            assert [job_input.input_type for job_input in inputs] == ["resume"]
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()
