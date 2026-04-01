from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.api.dependencies import get_codex_bridge_client
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import AgentRuntimeRepository
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.job_inputs import JobInputRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.runtime_pools import RuntimePoolRecord, RuntimePoolRepository


class FakeBridge:
    """Deterministic bridge for reliability tests."""

    def __init__(self) -> None:
        self.turn_interrupt_calls: list[dict[str, object]] = []

    async def turn_interrupt(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.turn_interrupt_calls.append(payload)
        return {"result": {"turn_id": payload.get("turn_id"), "interrupted": True}}

    async def thread_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {"result": {"thread_id": "thr_fake"}}

    async def thread_resume(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {"result": {"thread_id": "thr_fake", "resumed": True}}

    async def turn_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {"result": {"turn_id": "turn_fake", "status": "running"}}

    async def turn_steer(self, params: dict[str, object] | None = None) -> dict[str, object]:
        return {"result": {"turn_id": "turn_fake", "steered": True}}

    async def thread_compact_start(
        self,
        params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {"result": {"thread_id": "thr_fake", "compacted": True}}


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'reliability.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _build_app() -> tuple[object, FakeBridge]:
    app_main.get_config.cache_clear()
    app = app_main.create_app()
    bridge = FakeBridge()
    app.dependency_overrides[get_codex_bridge_client] = lambda: bridge
    return app, bridge


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


def _create_session(
    client: TestClient,
    *,
    title: str,
    goal: str,
    lead_agent_id: str,
) -> str:
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


def _add_participant(
    client: TestClient,
    *,
    session_id: str,
    agent_id: str,
    role: str,
) -> None:
    response = client.post(
        f"/api/v1/sessions/{session_id}/participants",
        json={"agent_id": agent_id, "role": role},
    )
    assert response.status_code == 201


def _seed_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    status: str,
    thread_id: str | None = None,
    turn_id: str | None = None,
    channel_key: str = "general",
) -> None:
    now = "2026-04-01T00:00:00Z"
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                assigned_agent_id=agent_id,
                runtime_id=None,
                source_message_id=None,
                parent_job_id=None,
                title=f"Job {job_id}",
                instructions=f"Instructions for {job_id}",
                status=status,
                hop_count=0,
                priority="normal",
                codex_runtime_id=None,
                codex_thread_id=thread_id,
                active_turn_id=turn_id,
                last_known_turn_status=status,
                result_summary=None,
                error_code=None,
                error_message=None,
                started_at=now if status != "queued" else None,
                completed_at=None,
                created_at=now,
                updated_at=now,
                channel_key=channel_key,
            )
        )
    )


def _seed_completed_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    channel_key: str = "general",
) -> None:
    _seed_job(
        database_url,
        job_id=job_id,
        session_id=session_id,
        agent_id=agent_id,
        status="completed",
        thread_id=None,
        turn_id=None,
        channel_key=channel_key,
    )


def test_retry_resume_and_interrupt_are_idempotent(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app, bridge = _build_app()

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
                title="Reliability",
                goal="Exercise retry and interrupt idempotency",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=lead_agent_id,
                role="planner",
            )
            runtime_repository = AgentRuntimeRepository(database_url)
            runtime = next(
                item
                for item in asyncio.run(runtime_repository.list())
                if item.agent_id == lead_agent_id
            )
            assert runtime is not None
            asyncio.run(
                runtime_repository.update(
                    replace(
                        runtime,
                        runtime_status="offline",
                        last_heartbeat_at=None,
                        updated_at="2026-04-01T00:00:00Z",
                    )
                )
            )

            retry_job_id = "job_retry_001"
            _seed_job(
                database_url,
                job_id=retry_job_id,
                session_id=session_id,
                agent_id=lead_agent_id,
                status="failed",
            )

            retry_first = client.post(f"/api/v1/jobs/{retry_job_id}/retry")
            assert retry_first.status_code == 200
            retry_second = client.post(f"/api/v1/jobs/{retry_job_id}/retry")
            assert retry_second.status_code == 200

            job_input_repository = JobInputRepository(database_url)
            retry_inputs = asyncio.run(job_input_repository.list_by_job(retry_job_id))
            assert [item.input_type for item in retry_inputs] == ["retry"]

            resume_job_id = "job_resume_001"
            _seed_job(
                database_url,
                job_id=resume_job_id,
                session_id=session_id,
                agent_id=lead_agent_id,
                status="input_required",
            )

            resume_first = client.post(f"/api/v1/jobs/{resume_job_id}/resume")
            assert resume_first.status_code == 200
            resume_second = client.post(f"/api/v1/jobs/{resume_job_id}/resume")
            assert resume_second.status_code == 200

            resume_inputs = asyncio.run(job_input_repository.list_by_job(resume_job_id))
            assert [item.input_type for item in resume_inputs] == ["resume"]

            interrupt_job_id = "job_interrupt_001"
            _seed_job(
                database_url,
                job_id=interrupt_job_id,
                session_id=session_id,
                agent_id=lead_agent_id,
                status="running",
                thread_id="thr_interrupt",
                turn_id="turn_interrupt",
            )

            cancel_first = client.post(f"/api/v1/jobs/{interrupt_job_id}/cancel")
            assert cancel_first.status_code == 200
            cancel_second = client.post(f"/api/v1/jobs/{interrupt_job_id}/cancel")
            assert cancel_second.status_code == 200

            assert len(bridge.turn_interrupt_calls) == 1
            job_repository = JobRepository(database_url)
            interrupted_job = asyncio.run(job_repository.get(interrupt_job_id))
            assert interrupted_job is not None
            assert interrupted_job.status == "canceled"
    finally:
        app.dependency_overrides.pop(get_codex_bridge_client, None)
        app_main.get_config.cache_clear()


def test_review_decision_replay_does_not_duplicate_side_effects(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app, _bridge = _build_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead",
                role="planner",
                is_lead=True,
            )
            builder_agent_id = _create_agent(
                client,
                display_name="Builder",
                role="builder",
                is_lead=False,
            )
            reviewer_agent_id = _create_agent(
                client,
                display_name="Reviewer",
                role="reviewer",
                is_lead=False,
            )
            session_id = _create_session(
                client,
                title="Review replay",
                goal="Exercise review decision idempotency",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=lead_agent_id,
                role="planner",
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=builder_agent_id,
                role="builder",
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=reviewer_agent_id,
                role="reviewer",
            )

            source_job_id = "job_review_replay"
            _seed_completed_job(
                database_url,
                job_id=source_job_id,
                session_id=session_id,
                agent_id=builder_agent_id,
                channel_key="general",
            )
            artifact_repository = ArtifactRepository(database_url)
            asyncio.run(
                artifact_repository.create(
                    ArtifactRecord(
                        id="art_review_replay",
                        job_id=source_job_id,
                        session_id=session_id,
                        source_message_id=None,
                        artifact_type="final_text",
                        title="Review source artifact",
                        content_text="Source output for review replay",
                        file_path=None,
                        file_name="review.txt",
                        mime_type="text/plain",
                        size_bytes=len("Source output for review replay".encode("utf-8")),
                        checksum_sha256="checksum-review-replay",
                        metadata_json=json.dumps({"kind": "review_source"}, sort_keys=True),
                        created_at="2026-04-01T00:00:00Z",
                        updated_at="2026-04-01T00:00:00Z",
                        channel_key="general",
                    )
                )
            )

            review_response = client.post(
                f"/api/v1/sessions/{session_id}/reviews",
                json={
                    "source_job_id": source_job_id,
                    "reviewer_agent_id": reviewer_agent_id,
                    "review_scope": "job",
                    "review_channel_key": "review",
                    "notes": "Check the output.",
                },
            )
            assert review_response.status_code == 201
            review_id = review_response.json()["review"]["id"]

            first_decision = client.post(
                f"/api/v1/reviews/{review_id}/decision",
                json={
                    "decision": "changes_requested",
                    "summary": "Needs one more pass.",
                    "required_changes": ["Add a failing-path test"],
                    "notes": "Retry the same decision safely.",
                    "revision_priority": "high",
                },
            )
            assert first_decision.status_code == 200
            first_body = first_decision.json()["review"]
            revision_job_id = first_body["revision_job_id"]
            assert revision_job_id is not None
            summary_artifact_id = first_body["summary_artifact_id"]
            assert summary_artifact_id is not None

            second_decision = client.post(
                f"/api/v1/reviews/{review_id}/decision",
                json={
                    "decision": "changes_requested",
                    "summary": "Needs one more pass.",
                    "required_changes": ["Add a failing-path test"],
                    "notes": "Retry the same decision safely.",
                    "revision_priority": "high",
                },
            )
            assert second_decision.status_code == 200
            second_body = second_decision.json()["review"]
            assert second_body["revision_job_id"] == revision_job_id
            assert second_body["summary_artifact_id"] == summary_artifact_id

            job_repository = JobRepository(database_url)
            revision_jobs = [
                job
                for job in asyncio.run(job_repository.list_by_session(session_id))
                if job.parent_job_id == source_job_id
            ]
            assert len(revision_jobs) == 1

            review_repository = ReviewRepository(database_url)
            stored_review = asyncio.run(review_repository.get(review_id))
            assert stored_review is not None
            assert stored_review.review_status == "changes_requested"
    finally:
        app_main.get_config.cache_clear()


def test_orchestration_gate_replay_reuses_pending_request(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app, _bridge = _build_app()

    try:
        with TestClient(app) as client:
            lead_agent_id = _create_agent(
                client,
                display_name="Lead",
                role="planner",
                is_lead=True,
            )
            builder_agent_id = _create_agent(
                client,
                display_name="Builder",
                role="builder",
                is_lead=False,
            )
            reviewer_agent_id = _create_agent(
                client,
                display_name="Reviewer",
                role="reviewer",
                is_lead=False,
            )
            session_id = _create_session(
                client,
                title="Gate replay",
                goal="Exercise orchestration request idempotency",
                lead_agent_id=lead_agent_id,
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=lead_agent_id,
                role="planner",
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=builder_agent_id,
                role="builder",
            )
            _add_participant(
                client,
                session_id=session_id,
                agent_id=reviewer_agent_id,
                role="reviewer",
            )

            source_job_id = "job_gate_replay"
            _seed_completed_job(
                database_url,
                job_id=source_job_id,
                session_id=session_id,
                agent_id=builder_agent_id,
                channel_key="general",
            )

            start_response = client.post(f"/api/v1/orchestration/sessions/{session_id}/start")
            assert start_response.status_code == 201

            gate_payload = {
                "source_job_id": source_job_id,
                "gate_type": "review_required",
                "success_phase_key": "finalize",
                "failure_phase_key": "revise",
                "reviewer_agent_id": reviewer_agent_id,
                "requested_by_agent_id": lead_agent_id,
                "notes": "First gate request.",
            }
            first_gate = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json=gate_payload,
            )
            assert first_gate.status_code == 201
            first_body = first_gate.json()

            second_gate = client.post(
                f"/api/v1/orchestration/sessions/{session_id}/gate",
                json=gate_payload,
            )
            assert second_gate.status_code == 201
            second_body = second_gate.json()

            assert second_body["review_id"] == first_body["review_id"]
            assert second_body["handoff_job_id"] == first_body["handoff_job_id"]
            assert second_body["transition_artifact_id"] == first_body["transition_artifact_id"]

            review_repository = ReviewRepository(database_url)
            assert len(asyncio.run(review_repository.list_by_session(session_id))) == 1
            job_repository = JobRepository(database_url)
            gate_jobs = [
                job
                for job in asyncio.run(job_repository.list_by_session(session_id))
                if job.parent_job_id == source_job_id
            ]
            assert len(gate_jobs) == 1
    finally:
        app_main.get_config.cache_clear()


def test_runtime_pool_diagnostics_tolerate_corrupt_json(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app, _bridge = _build_app()

    try:
        now = "2026-04-01T00:00:00Z"
        asyncio.run(
            RuntimePoolRepository(database_url).create(
                RuntimePoolRecord(
                    id="rpl_corrupt",
                    pool_key="corrupt_pool",
                    title="Corrupt Pool",
                    description="Pool with malformed JSON metadata",
                    runtime_kind="codex",
                    preferred_transport_kind="stdio",
                    required_capabilities_json="{not valid json",
                    fallback_pool_key=None,
                    max_active_contexts=1,
                    default_isolation_mode="isolated",
                    pool_status="ready",
                    metadata_json="{still not valid",
                    is_default=0,
                    sort_order=90,
                    created_at=now,
                    updated_at=now,
                )
            )
        )

        with TestClient(app) as client:
            response = client.get("/api/v1/runtime-pools/diagnostics")
            assert response.status_code == 200
            body = response.json()["diagnostics"]
            corrupt_pool = next(
                pool for pool in body["pools"] if pool["pool_key"] == "corrupt_pool"
            )
            assert corrupt_pool["required_capabilities"] == []
            assert corrupt_pool["metadata"] is None
    finally:
        app_main.get_config.cache_clear()
