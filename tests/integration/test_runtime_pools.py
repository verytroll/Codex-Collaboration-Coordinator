from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import app.main as app_main
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.sessions import SessionRecord, SessionRepository


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'runtime_pools.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


def _create_agent(client: TestClient) -> tuple[str, str | None]:
    response = client.post(
        "/api/v1/agents",
        json={
            "display_name": "Runtime Lead",
            "role": "builder",
            "is_lead": True,
            "runtime_kind": "codex",
            "runtime_config": {
                "workspace_path": "/workspace/project",
                "sandbox_mode": "workspace-write",
            },
        },
    )
    assert response.status_code == 201
    agent_body = response.json()["agent"]
    return agent_body["id"], agent_body["runtime_id"]


def _create_agent_without_runtime(
    database_url: str,
    *,
    agent_id: str,
    display_name: str,
) -> None:
    asyncio.run(
        AgentRepository(database_url).create(
            AgentRecord(
                id=agent_id,
                display_name=display_name,
                role="builder",
                is_lead_default=1,
                runtime_kind="codex",
                capabilities_json='{"can_code": true}',
                default_config_json=None,
                status="active",
                created_at="2026-04-01T00:00:00Z",
                updated_at="2026-04-01T00:00:00Z",
            )
        )
    )


def _create_session(
    database_url: str,
    *,
    session_id: str,
    lead_agent_id: str,
    title: str,
) -> None:
    asyncio.run(
        SessionRepository(database_url).create(
            SessionRecord(
                id=session_id,
                title=title,
                goal="Exercise runtime pools",
                status="active",
                lead_agent_id=lead_agent_id,
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=None,
                created_at="2026-04-01T00:00:00Z",
                updated_at="2026-04-01T00:00:00Z",
            )
        )
    )


def _create_job(
    database_url: str,
    *,
    job_id: str,
    session_id: str,
    agent_id: str,
    runtime_id: str | None,
    title: str,
) -> None:
    asyncio.run(
        JobRepository(database_url).create(
            JobRecord(
                id=job_id,
                session_id=session_id,
                assigned_agent_id=agent_id,
                runtime_id=runtime_id,
                source_message_id=None,
                parent_job_id=None,
                title=title,
                instructions=title,
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
                created_at="2026-04-01T00:00:00Z",
                updated_at="2026-04-01T00:00:00Z",
            )
        )
    )


def _create_runtime(
    database_url: str,
    *,
    runtime_id: str,
    agent_id: str,
    runtime_status: str = "online",
) -> None:
    asyncio.run(
        AgentRuntimeRepository(database_url).create(
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
                last_heartbeat_at="2026-04-01T00:00:00Z" if runtime_status != "offline" else None,
                created_at="2026-04-01T00:00:00Z",
                updated_at="2026-04-01T00:00:00Z",
            )
        )
    )


def test_runtime_pool_assignment_recovery_and_fallback(tmp_path, monkeypatch) -> None:
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _migrate(database_url)
    app_main.get_config.cache_clear()
    app = app_main.create_app()

    try:
        with TestClient(app) as client:
            lead_agent_id, runtime_id = _create_agent(client)
            assert runtime_id is not None
            session_id = "ses_runtime_pool"
            _create_session(
                database_url,
                session_id=session_id,
                lead_agent_id=lead_agent_id,
                title="Runtime pool session",
            )

            pool_response = client.post(
                "/api/v1/runtime-pools",
                json={
                    "pool_key": "gpu_only",
                    "title": "GPU Only",
                    "description": "Requires GPU capability and falls back to general shared",
                    "runtime_kind": "codex",
                    "preferred_transport_kind": "stdio",
                    "required_capabilities": ["gpu"],
                    "fallback_pool_key": "general_shared",
                    "max_active_contexts": 1,
                    "default_isolation_mode": "isolated",
                    "pool_status": "ready",
                    "metadata": {"lane": "gpu"},
                    "is_default": False,
                    "sort_order": 30,
                },
            )
            assert pool_response.status_code == 201
            assert pool_response.json()["pool"]["pool_key"] == "gpu_only"

            pools_response = client.get("/api/v1/runtime-pools")
            assert pools_response.status_code == 200
            pool_keys = [pool["pool_key"] for pool in pools_response.json()["pools"]]
            assert pool_keys[:2] == ["general_shared", "isolated_work"]
            assert "gpu_only" in pool_keys

            first_job_id = "job_runtime_pool_1"
            _create_job(
                database_url,
                job_id=first_job_id,
                session_id=session_id,
                agent_id=lead_agent_id,
                runtime_id=runtime_id,
                title="Work in isolated pool",
            )
            first_assign_response = client.post(
                "/api/v1/runtime-pools/isolated_work/assign",
                json={
                    "job_id": first_job_id,
                    "preferred_pool_key": "isolated_work",
                    "required_capabilities": [],
                },
            )
            assert first_assign_response.status_code == 200

            first_context_response = client.get(
                "/api/v1/work-contexts",
                params={"job_id": first_job_id},
            )
            assert first_context_response.status_code == 200
            first_context = first_context_response.json()["contexts"][0]
            assert first_context["runtime_pool_key"] == "isolated_work"
            assert first_context["context_status"] == "active"
            assert first_context["runtime_id"] == runtime_id

            diagnostics_response = client.get("/api/v1/runtime-pools/diagnostics")
            assert diagnostics_response.status_code == 200
            diagnostics = diagnostics_response.json()["diagnostics"]["pools"]
            isolated_pool = next(
                pool for pool in diagnostics if pool["pool_key"] == "isolated_work"
            )
            assert isolated_pool["active_context_count"] == 1
            assert isolated_pool["utilization_ratio"] == 1.0

            recovery_agent_id = "agt_recovery"
            _create_agent_without_runtime(
                database_url,
                agent_id=recovery_agent_id,
                display_name="Runtime Recovery",
            )
            recovery_session_id = "ses_recovery"
            _create_session(
                database_url,
                session_id=recovery_session_id,
                lead_agent_id=recovery_agent_id,
                title="Recovery session",
            )

            second_job_id = "job_runtime_pool_2"
            _create_job(
                database_url,
                job_id=second_job_id,
                session_id=recovery_session_id,
                agent_id=recovery_agent_id,
                runtime_id=None,
                title="Needs recovery",
            )
            second_assign_response = client.post(
                "/api/v1/runtime-pools/isolated_work/assign",
                json={
                    "job_id": second_job_id,
                    "preferred_pool_key": "isolated_work",
                    "required_capabilities": [],
                },
            )
            assert second_assign_response.status_code == 200

            second_context_response = client.get(
                "/api/v1/work-contexts",
                params={"job_id": second_job_id},
            )
            assert second_context_response.status_code == 200
            second_context = second_context_response.json()["contexts"][0]
            assert second_context["runtime_pool_key"] == "general_shared"
            assert second_context["context_status"] == "waiting_for_runtime"
            assert second_context["runtime_id"] is None

            recovered_runtime_id = "rt_recovered"
            _create_runtime(
                database_url,
                runtime_id=recovered_runtime_id,
                agent_id=recovery_agent_id,
                runtime_status="online",
            )
            recover_response = client.post(f"/api/v1/work-contexts/{second_context['id']}/recover")
            assert recover_response.status_code == 200
            recovered_context = recover_response.json()["context"]
            assert recovered_context["context_status"] == "recovered"
            assert recovered_context["runtime_id"] == recovered_runtime_id

            fallback_job_id = "job_runtime_pool_3"
            _create_job(
                database_url,
                job_id=fallback_job_id,
                session_id=session_id,
                agent_id=lead_agent_id,
                runtime_id=runtime_id,
                title="Fallback through pool",
            )
            fallback_response = client.post(
                "/api/v1/runtime-pools/gpu_only/assign",
                json={
                    "job_id": fallback_job_id,
                    "preferred_pool_key": "gpu_only",
                    "required_capabilities": ["gpu"],
                },
            )
            assert fallback_response.status_code == 200

            fallback_context_response = client.get(
                "/api/v1/work-contexts",
                params={"job_id": fallback_job_id},
            )
            assert fallback_context_response.status_code == 200
            fallback_context = fallback_context_response.json()["contexts"][0]
            assert fallback_context["runtime_pool_key"] == "general_shared"
    finally:
        app_main.get_config.cache_clear()
