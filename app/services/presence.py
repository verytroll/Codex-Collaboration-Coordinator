"""Presence tracking service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.repositories.agents import AgentRuntimeRecord, AgentRuntimeRepository
from app.repositories.presence import PresenceHeartbeatRecord, PresenceRepository
from app.services.runtime_service import RuntimeService

PRESENCE_STATUSES = {"online", "offline", "busy", "unknown"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class PresenceSnapshot:
    """Resolved presence summary for an agent."""

    agent_id: str
    runtime_id: str | None
    presence: str
    heartbeat_at: str | None


class PresenceService:
    """Record and resolve agent presence."""

    def __init__(
        self,
        *,
        presence_repository: PresenceRepository,
        runtime_repository: AgentRuntimeRepository,
        runtime_service: RuntimeService,
    ) -> None:
        self.presence_repository = presence_repository
        self.runtime_repository = runtime_repository
        self.runtime_service = runtime_service

    async def record_heartbeat(
        self,
        *,
        agent_id: str,
        runtime_id: str | None = None,
        presence: str = "online",
        details: dict[str, Any] | None = None,
        heartbeat_at: str | None = None,
    ) -> PresenceHeartbeatRecord:
        """Persist a heartbeat and mirror runtime status when possible."""
        normalized_presence = self._normalize_presence(presence)
        resolved_runtime_id = runtime_id
        if resolved_runtime_id is None:
            latest_runtime = await self.runtime_service.get_latest_runtime_for_agent(agent_id)
            resolved_runtime_id = latest_runtime.id if latest_runtime is not None else None

        resolved_heartbeat_at = heartbeat_at or _utc_now()
        if resolved_runtime_id is not None and normalized_presence in {"online", "offline", "busy"}:
            await self.runtime_service.set_runtime_status(
                resolved_runtime_id,
                normalized_presence,
                heartbeat_at=resolved_heartbeat_at,
            )

        heartbeat = PresenceHeartbeatRecord(
            id=f"pre_{agent_id}_{resolved_heartbeat_at.replace(':', '').replace('-', '')}",
            agent_id=agent_id,
            runtime_id=resolved_runtime_id,
            presence=normalized_presence,
            heartbeat_at=resolved_heartbeat_at,
            details_json=json.dumps(details, sort_keys=True) if details is not None else None,
            created_at=resolved_heartbeat_at,
        )
        return await self.presence_repository.create(heartbeat)

    async def get_snapshot(self, agent_id: str) -> PresenceSnapshot:
        """Resolve the latest presence snapshot for an agent."""
        heartbeats = await self.presence_repository.list_by_agent(agent_id)
        if heartbeats:
            latest = max(heartbeats, key=lambda heartbeat: (heartbeat.heartbeat_at, heartbeat.id))
            return PresenceSnapshot(
                agent_id=agent_id,
                runtime_id=latest.runtime_id,
                presence=latest.presence,
                heartbeat_at=latest.heartbeat_at,
            )

        runtime = await self.runtime_service.get_latest_runtime_for_agent(agent_id)
        if runtime is None:
            return PresenceSnapshot(
                agent_id=agent_id,
                runtime_id=None,
                presence="unknown",
                heartbeat_at=None,
            )
        return PresenceSnapshot(
            agent_id=agent_id,
            runtime_id=runtime.id,
            presence=runtime.runtime_status
            if runtime.runtime_status in PRESENCE_STATUSES
            else "unknown",
            heartbeat_at=runtime.last_heartbeat_at,
        )

    async def list_heartbeats(self, agent_id: str) -> list[PresenceHeartbeatRecord]:
        """List all heartbeats for an agent."""
        return await self.presence_repository.list_by_agent(agent_id)

    async def list_latest_runtime_heartbeats(self) -> list[AgentRuntimeRecord]:
        """Return runtimes ordered by recency for inspection."""
        runtimes = await self.runtime_repository.list()
        return sorted(runtimes, key=lambda runtime: (runtime.last_heartbeat_at or "", runtime.id))

    @staticmethod
    def _normalize_presence(presence: str) -> str:
        normalized = presence.strip().lower()
        if normalized not in PRESENCE_STATUSES:
            raise ValueError(f"Unsupported presence status: {presence}")
        return normalized
