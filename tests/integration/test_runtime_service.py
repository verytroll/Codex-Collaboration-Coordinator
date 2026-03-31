from __future__ import annotations

import asyncio

from app.db.migrations import DEFAULT_MIGRATIONS_DIR, migrate_sqlite
from app.repositories.agents import (
    AgentRecord,
    AgentRepository,
    AgentRuntimeRecord,
    AgentRuntimeRepository,
)
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.runtime_service import RuntimeService
from app.services.thread_mapping import ThreadMappingService


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'runtime_service.db').as_posix()}"


def _migrate(database_url: str) -> None:
    asyncio.run(migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR))


class FakeBridge:
    """Test double for the Codex bridge."""

    def __init__(self) -> None:
        self.thread_start_calls = []
        self.thread_resume_calls = []

    async def thread_start(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.thread_start_calls.append(payload)
        return {"result": {"thread_id": f"thr_{len(self.thread_start_calls)}"}}

    async def thread_resume(self, params: dict[str, object] | None = None) -> dict[str, object]:
        payload = dict(params or {})
        self.thread_resume_calls.append(payload)
        return {"result": {"thread_id": payload["thread_id"], "resumed": True}}


def test_runtime_service_updates_runtime_status(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)
    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    runtime_service = RuntimeService(runtime_repository)

    asyncio.run(
        agent_repository.create(
            AgentRecord(
                id="agt_001",
                display_name="Runtime Agent",
                role="builder",
                is_lead_default=0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )
    runtime = AgentRuntimeRecord(
        id="rt_001",
        agent_id="agt_001",
        runtime_kind="codex",
        transport_kind="stdio",
        transport_config_json=None,
        workspace_path="/workspace/project",
        approval_policy=None,
        sandbox_policy="workspace-write",
        runtime_status="starting",
        last_heartbeat_at=None,
        created_at="2026-03-31T00:00:00Z",
        updated_at="2026-03-31T00:00:00Z",
    )

    asyncio.run(runtime_repository.create(runtime))
    updated = asyncio.run(
        runtime_service.set_online(runtime.id, heartbeat_at="2026-03-31T00:01:00Z")
    )

    assert updated.runtime_status == "online"
    assert updated.last_heartbeat_at == "2026-03-31T00:01:00Z"
    assert asyncio.run(runtime_service.get_latest_runtime_for_agent("agt_001")) == updated


def test_thread_mapping_creates_and_reuses_thread(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    _migrate(database_url)

    agent_repository = AgentRepository(database_url)
    runtime_repository = AgentRuntimeRepository(database_url)
    session_repository = SessionRepository(database_url)
    runtime_service = RuntimeService(runtime_repository)
    mapping_service = ThreadMappingService(runtime_service)
    bridge = FakeBridge()

    asyncio.run(
        agent_repository.create(
            AgentRecord(
                id="agt_002",
                display_name="Builder",
                role="builder",
                is_lead_default=0,
                runtime_kind="codex",
                capabilities_json=None,
                default_config_json=None,
                status="active",
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )
    asyncio.run(
        runtime_repository.create(
            AgentRuntimeRecord(
                id="rt_002",
                agent_id="agt_002",
                runtime_kind="codex",
                transport_kind="stdio",
                transport_config_json=None,
                workspace_path="/workspace/project",
                approval_policy=None,
                sandbox_policy="workspace-write",
                runtime_status="online",
                last_heartbeat_at="2026-03-31T00:00:00Z",
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )
    asyncio.run(
        session_repository.create(
            SessionRecord(
                id="ses_002",
                title="Thread mapping",
                goal=None,
                status="active",
                lead_agent_id=None,
                active_phase_id=None,
                loop_guard_status="normal",
                loop_guard_reason=None,
                last_message_at=None,
                created_at="2026-03-31T00:00:00Z",
                updated_at="2026-03-31T00:00:00Z",
            )
        )
    )

    first_mapping, created_first = asyncio.run(
        mapping_service.get_or_create_thread(
            session_id="ses_002",
            agent_id="agt_002",
            bridge=bridge,
        )
    )
    second_mapping, created_second = asyncio.run(
        mapping_service.get_or_create_thread(
            session_id="ses_002",
            agent_id="agt_002",
            bridge=bridge,
        )
    )

    assert created_first is True
    assert created_second is False
    assert first_mapping.codex_thread_id == "thr_1"
    assert second_mapping.codex_thread_id == "thr_1"
    assert len(bridge.thread_start_calls) == 1
    assert len(bridge.thread_resume_calls) == 1
    assert bridge.thread_resume_calls[0]["thread_id"] == "thr_1"
