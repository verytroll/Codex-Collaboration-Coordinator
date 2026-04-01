"""Loop guard service based on relay edges."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord, JobRepository
from app.repositories.relay_edges import RelayEdgeRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.session_events import record_session_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class LoopGuardDecision:
    """Result of evaluating a relay against loop guard policy."""

    should_pause: bool
    reason: str | None
    prior_edges: int


class LoopGuardService:
    """Evaluate and persist loop guard state."""

    def __init__(
        self,
        *,
        relay_edge_repository: RelayEdgeRepository,
        job_repository: JobRepository,
        job_event_repository: JobEventRepository,
        session_repository: SessionRepository,
        session_event_repository: SessionEventRepository,
        max_relay_edges_per_agent: int = 3,
    ) -> None:
        self.relay_edge_repository = relay_edge_repository
        self.job_repository = job_repository
        self.job_event_repository = job_event_repository
        self.session_repository = session_repository
        self.session_event_repository = session_event_repository
        self.max_relay_edges_per_agent = max_relay_edges_per_agent

    async def evaluate(self, job: JobRecord) -> LoopGuardDecision:
        """Return whether a relay should be paused."""
        edges = await self.relay_edge_repository.list_by_session(job.session_id)
        matching_edges = [edge for edge in edges if edge.target_agent_id == job.assigned_agent_id]
        should_pause = len(matching_edges) + 1 >= self.max_relay_edges_per_agent
        reason = None
        if should_pause:
            reason = (
                "Loop guard paused relay for agent "
                f"{job.assigned_agent_id} after {len(matching_edges)} prior relays"
            )
        return LoopGuardDecision(
            should_pause=should_pause,
            reason=reason,
            prior_edges=len(matching_edges),
        )

    async def pause_job(self, job: JobRecord, *, reason: str) -> JobRecord:
        """Persist a paused-by-loop-guard job state."""
        now = _utc_now()
        updated_job = JobRecord(
            id=job.id,
            session_id=job.session_id,
            channel_key=job.channel_key,
            assigned_agent_id=job.assigned_agent_id,
            runtime_id=job.runtime_id,
            source_message_id=job.source_message_id,
            parent_job_id=job.parent_job_id,
            title=job.title,
            instructions=job.instructions,
            status="paused_by_loop_guard",
            hop_count=job.hop_count,
            priority=job.priority,
            codex_runtime_id=job.codex_runtime_id,
            codex_thread_id=job.codex_thread_id,
            active_turn_id=job.active_turn_id,
            last_known_turn_status="paused_by_loop_guard",
            result_summary=job.result_summary,
            error_code=job.error_code,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=now,
            created_at=job.created_at,
            updated_at=now,
        )
        await self.job_repository.update(updated_job)
        await self._record_job_event(updated_job, reason=reason, created_at=now)
        session = await self._get_session(job.session_id)
        await self.session_repository.update(
            SessionRecord(
                id=session.id,
                title=session.title,
                goal=session.goal,
                status=session.status,
                lead_agent_id=session.lead_agent_id,
                active_phase_id=session.active_phase_id,
                loop_guard_status="paused",
                loop_guard_reason=reason,
                last_message_at=session.last_message_at,
                template_key=session.template_key,
                created_at=session.created_at,
                updated_at=now,
            )
        )
        await record_session_event(
            self.session_event_repository,
            session_id=job.session_id,
            event_type="loop_guard_triggered",
            actor_type="system",
            actor_id=None,
            payload={
                "job_id": job.id,
                "agent_id": job.assigned_agent_id,
                "reason": reason,
            },
            created_at=now,
        )
        return updated_job

    async def _record_job_event(
        self,
        job: JobRecord,
        *,
        reason: str,
        created_at: str,
    ) -> JobEventRecord:
        event = JobEventRecord(
            id=f"jbe_{uuid4().hex}",
            job_id=job.id,
            session_id=job.session_id,
            event_type="job.paused_by_loop_guard",
            event_payload_json=json.dumps(
                {
                    "agent_id": job.assigned_agent_id,
                    "reason": reason,
                },
                sort_keys=True,
            ),
            created_at=created_at,
        )
        return await self.job_event_repository.create(event)

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        return session
