"""Runtime status service for agent runtimes."""

from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.agents import AgentRuntimeRecord, AgentRuntimeRepository

RUNTIME_STATUSES = {"starting", "online", "offline", "crashed", "busy"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RuntimeService:
    """Manage runtime status and lookup for agent runtimes."""

    def __init__(self, runtime_repository: AgentRuntimeRepository) -> None:
        self.runtime_repository = runtime_repository

    async def get_runtime(self, runtime_id: str) -> AgentRuntimeRecord | None:
        """Fetch a runtime by identifier."""
        return await self.runtime_repository.get(runtime_id)

    async def get_latest_runtime_for_agent(
        self,
        agent_id: str,
    ) -> AgentRuntimeRecord | None:
        """Return the most recent runtime for an agent."""
        runtimes = await self.runtime_repository.list()
        matching = [runtime for runtime in runtimes if runtime.agent_id == agent_id]
        if not matching:
            return None
        return max(matching, key=lambda runtime: (runtime.created_at, runtime.id))

    async def set_runtime_status(
        self,
        runtime_id: str,
        runtime_status: str,
        *,
        heartbeat_at: str | None = None,
    ) -> AgentRuntimeRecord:
        """Update runtime status and optional heartbeat timestamp."""
        if runtime_status not in RUNTIME_STATUSES:
            raise ValueError(f"Unsupported runtime status: {runtime_status}")

        runtime = await self.runtime_repository.get(runtime_id)
        if runtime is None:
            raise LookupError(f"Runtime not found: {runtime_id}")

        updated = AgentRuntimeRecord(
            id=runtime.id,
            agent_id=runtime.agent_id,
            runtime_kind=runtime.runtime_kind,
            transport_kind=runtime.transport_kind,
            transport_config_json=runtime.transport_config_json,
            workspace_path=runtime.workspace_path,
            approval_policy=runtime.approval_policy,
            sandbox_policy=runtime.sandbox_policy,
            runtime_status=runtime_status,
            last_heartbeat_at=(
                heartbeat_at if heartbeat_at is not None else runtime.last_heartbeat_at
            ),
            created_at=runtime.created_at,
            updated_at=_utc_now(),
        )
        return await self.runtime_repository.update(updated)

    async def set_online(
        self,
        runtime_id: str,
        *,
        heartbeat_at: str | None = None,
    ) -> AgentRuntimeRecord:
        """Mark a runtime as online."""
        return await self.set_runtime_status(
            runtime_id,
            "online",
            heartbeat_at=heartbeat_at or _utc_now(),
        )

    async def set_busy(
        self,
        runtime_id: str,
        *,
        heartbeat_at: str | None = None,
    ) -> AgentRuntimeRecord:
        """Mark a runtime as busy."""
        return await self.set_runtime_status(
            runtime_id,
            "busy",
            heartbeat_at=heartbeat_at or _utc_now(),
        )

    async def set_offline(
        self,
        runtime_id: str,
        *,
        heartbeat_at: str | None = None,
    ) -> AgentRuntimeRecord:
        """Mark a runtime as offline."""
        return await self.set_runtime_status(
            runtime_id,
            "offline",
            heartbeat_at=heartbeat_at,
        )
