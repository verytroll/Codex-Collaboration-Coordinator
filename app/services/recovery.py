"""Recovery service for restart rehydration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.repositories.agents import AgentRuntimeRepository
from app.repositories.jobs import JobRepository
from app.repositories.presence import PresenceRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.runtime_service import RuntimeService
from app.services.session_events import record_session_event
from app.services.thread_mapping import ThreadMappingRecord, ThreadMappingStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class RecoverySummary:
    """Summary of recovered runtime and thread state."""

    recovered_threads: int
    offline_runtimes: int


class RecoveryService:
    """Rehydrate in-memory mappings and stale runtime status from persisted state."""

    def __init__(
        self,
        *,
        job_repository: JobRepository,
        runtime_repository: AgentRuntimeRepository,
        presence_repository: PresenceRepository,
        session_repository: SessionRepository,
        session_event_repository: SessionEventRepository,
        runtime_service: RuntimeService,
        thread_mapping_store: ThreadMappingStore,
        stale_after_minutes: int = 10,
    ) -> None:
        self.job_repository = job_repository
        self.runtime_repository = runtime_repository
        self.presence_repository = presence_repository
        self.session_repository = session_repository
        self.session_event_repository = session_event_repository
        self.runtime_service = runtime_service
        self.thread_mapping_store = thread_mapping_store
        self.stale_after_minutes = stale_after_minutes

    async def recover(self) -> RecoverySummary:
        """Recover runtime status and thread mappings from persisted rows."""
        offline_runtimes = await self._recover_runtimes()
        recovered_threads = await self._recover_thread_mappings()
        return RecoverySummary(
            recovered_threads=recovered_threads,
            offline_runtimes=offline_runtimes,
        )

    async def _recover_runtimes(self) -> int:
        runtimes = await self.runtime_repository.list()
        heartbeats = await self.presence_repository.list()
        latest_heartbeats: dict[str, tuple[str, str | None]] = {}
        for heartbeat in heartbeats:
            current = latest_heartbeats.get(heartbeat.agent_id)
            if current is None or heartbeat.heartbeat_at > current[0]:
                latest_heartbeats[heartbeat.agent_id] = (
                    heartbeat.heartbeat_at,
                    heartbeat.runtime_id,
                )

        offline = 0
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.stale_after_minutes)
        for runtime in runtimes:
            heartbeat = latest_heartbeats.get(runtime.agent_id)
            if heartbeat is None:
                continue
            heartbeat_time = _parse_utc(heartbeat[0])
            if heartbeat_time is None:
                continue
            if heartbeat_time >= cutoff:
                continue
            if runtime.runtime_status not in {"online", "busy", "starting"}:
                continue
            await self.runtime_service.set_offline(
                runtime.id,
                heartbeat_at=heartbeat[0],
            )
            offline += 1
        return offline

    async def _recover_thread_mappings(self) -> int:
        jobs = await self.job_repository.list()
        recovered = 0
        terminal_statuses = {"completed", "failed", "canceled", "paused_by_loop_guard"}
        for job in jobs:
            if job.codex_thread_id is None:
                continue
            if job.status in terminal_statuses:
                continue
            record = ThreadMappingRecord(
                id=f"ctm_{job.id}",
                session_id=job.session_id,
                agent_id=job.assigned_agent_id,
                runtime_id=job.runtime_id or job.codex_runtime_id,
                codex_thread_id=job.codex_thread_id,
                is_active=True,
                created_at=job.created_at,
                updated_at=_utc_now(),
            )
            self.thread_mapping_store.upsert(record)
            recovered += 1
            await record_session_event(
                self.session_event_repository,
                session_id=job.session_id,
                event_type="recovery.thread_rehydrated",
                actor_type="system",
                actor_id=None,
                payload={
                    "job_id": job.id,
                    "agent_id": job.assigned_agent_id,
                    "thread_id": job.codex_thread_id,
                },
                created_at=_utc_now(),
            )
        return recovered
