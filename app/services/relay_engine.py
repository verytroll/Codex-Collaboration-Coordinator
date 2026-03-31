"""Relay engine for executing jobs through CodexBridge."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from app.repositories.agents import AgentRecord, AgentRepository
from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord, JobRepository
from app.repositories.messages import MessageRecord, MessageRepository
from app.repositories.relay_edges import RelayEdgeRecord, RelayEdgeRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.runtime_service import RuntimeService
from app.services.session_events import record_session_event
from app.services.thread_mapping import ThreadMappingService


class CodexRelayBridge(Protocol):
    """Bridge interface used by the relay engine."""

    async def thread_start(self, params: dict[str, Any] | None = None) -> Any:
        """Start a thread."""

    async def thread_resume(self, params: dict[str, Any] | None = None) -> Any:
        """Resume a thread."""

    async def turn_start(self, params: dict[str, Any] | None = None) -> Any:
        """Start a turn."""

    async def turn_steer(self, params: dict[str, Any] | None = None) -> Any:
        """Steer a turn."""

    async def turn_interrupt(self, params: dict[str, Any] | None = None) -> Any:
        """Interrupt a turn."""

    async def thread_compact_start(self, params: dict[str, Any] | None = None) -> Any:
        """Compact a thread."""


@dataclass(frozen=True, slots=True)
class RelayExecutionResult:
    """Result from a relay or command action."""

    job_id: str
    session_id: str
    agent_id: str
    thread_id: str | None
    turn_id: str | None
    message_id: str | None
    event_type: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _unwrap_result(response: Any) -> dict[str, Any]:
    """Extract a JSON-RPC result payload."""
    if isinstance(response, dict):
        result = response.get("result", response)
        return result if isinstance(result, dict) else {"value": result}
    result = getattr(response, "result", response)
    if isinstance(result, dict):
        return result
    return {"value": result}


def _extract_text(payload: dict[str, Any], job: JobRecord) -> str:
    """Derive a publishable text payload from a bridge response."""
    for key in ("output_text", "output", "content", "message", "text", "summary"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(payload.get("value"), str) and str(payload["value"]).strip():
        return str(payload["value"]).strip()
    return f"Working on {job.title}"


def _extract_turn_id(payload: dict[str, Any], fallback: str) -> str:
    """Extract or synthesize a turn identifier."""
    turn_id = payload.get("turn_id") or payload.get("active_turn_id")
    if turn_id is not None:
        return str(turn_id)
    return fallback


class RelayEngine:
    """Execute jobs, interrupts, and compactions through CodexBridge."""

    def __init__(
        self,
        *,
        job_repository: JobRepository,
        job_event_repository: JobEventRepository,
        relay_edge_repository: RelayEdgeRepository,
        message_repository: MessageRepository,
        session_repository: SessionRepository,
        session_event_repository: SessionEventRepository,
        agent_repository: AgentRepository,
        runtime_service: RuntimeService,
        thread_mapping_service: ThreadMappingService,
        bridge: CodexRelayBridge,
    ) -> None:
        self.job_repository = job_repository
        self.job_event_repository = job_event_repository
        self.relay_edge_repository = relay_edge_repository
        self.message_repository = message_repository
        self.session_repository = session_repository
        self.session_event_repository = session_event_repository
        self.agent_repository = agent_repository
        self.runtime_service = runtime_service
        self.thread_mapping_service = thread_mapping_service
        self.bridge = bridge

    async def execute_job(
        self,
        job_id: str,
        *,
        relay_reason: str = "mention",
    ) -> RelayExecutionResult:
        """Start a job on Codex and publish the first output back to the session."""
        job = await self._get_job(job_id)
        session = await self._get_session(job.session_id)
        agent = await self._get_agent(job.assigned_agent_id)
        mapping, _ = await self.thread_mapping_service.get_or_create_thread(
            session_id=job.session_id,
            agent_id=job.assigned_agent_id,
            bridge=self.bridge,
        )

        now = _utc_now()
        turn_response = await self.bridge.turn_start(
            {
                "session_id": job.session_id,
                "job_id": job.id,
                "agent_id": job.assigned_agent_id,
                "thread_id": mapping.codex_thread_id,
                "runtime_id": mapping.runtime_id,
                "instructions": job.instructions or job.title,
                "source_message_id": job.source_message_id,
            }
        )
        turn_payload = _unwrap_result(turn_response)
        turn_id = _extract_turn_id(turn_payload, fallback=f"turn_{uuid4().hex}")
        output_text = _extract_text(turn_payload, job)

        updated_job = replace(
            job,
            runtime_id=job.runtime_id or mapping.runtime_id,
            codex_runtime_id=job.codex_runtime_id or mapping.runtime_id,
            codex_thread_id=mapping.codex_thread_id,
            active_turn_id=turn_id,
            last_known_turn_status=str(turn_payload.get("status", "running")),
            status="completed" if turn_payload.get("status") == "completed" else "running",
            started_at=job.started_at or now,
            completed_at=now if turn_payload.get("status") == "completed" else job.completed_at,
            updated_at=now,
        )
        await self.job_repository.update(updated_job)
        await self._record_job_event(
            job=updated_job,
            event_type="turn.started",
            payload={
                "thread_id": mapping.codex_thread_id,
                "turn_id": turn_id,
                "relay_reason": relay_reason,
            },
            created_at=now,
        )

        message = await self._publish_output_message(
            session=session,
            job=updated_job,
            agent=agent,
            content=output_text,
            reply_to_message_id=job.source_message_id,
            created_at=now,
        )
        await self._record_job_event(
            job=updated_job,
            event_type="relay.output.published",
            payload={
                "message_id": message.id,
                "thread_id": mapping.codex_thread_id,
                "turn_id": turn_id,
                "relay_reason": relay_reason,
            },
            created_at=now,
        )
        await self._record_relay_edge(job=updated_job, relay_reason=relay_reason, created_at=now)
        await self._record_session_event(
            session_id=session.id,
            event_type="relay.output.published",
            actor_type="agent",
            actor_id=agent.id,
            payload={
                "job_id": updated_job.id,
                "message_id": message.id,
                "thread_id": mapping.codex_thread_id,
                "turn_id": turn_id,
                "relay_reason": relay_reason,
            },
            created_at=now,
        )
        return RelayExecutionResult(
            job_id=updated_job.id,
            session_id=updated_job.session_id,
            agent_id=updated_job.assigned_agent_id,
            thread_id=mapping.codex_thread_id,
            turn_id=turn_id,
            message_id=message.id,
            event_type="relay.output.published",
        )

    async def interrupt_job(
        self,
        job_id: str,
        *,
        reason: str | None = None,
    ) -> RelayExecutionResult:
        """Interrupt the active turn for a job."""
        job = await self._get_job(job_id)
        session = await self._get_session(job.session_id)
        agent = await self._get_agent(job.assigned_agent_id)
        thread_id = job.codex_thread_id
        if thread_id is None:
            mapping = self.thread_mapping_service.store.get(job.session_id, job.assigned_agent_id)
            thread_id = mapping.codex_thread_id if mapping is not None else None
        if thread_id is None:
            raise LookupError(f"No Codex thread mapped for job {job.id}")

        turn_id = job.active_turn_id or thread_id
        now = _utc_now()
        response = await self.bridge.turn_interrupt(
            {
                "session_id": job.session_id,
                "job_id": job.id,
                "turn_id": turn_id,
                "thread_id": thread_id,
                "reason": reason,
            }
        )
        payload = _unwrap_result(response)

        updated_job = replace(
            job,
            status="canceled",
            last_known_turn_status="interrupted",
            completed_at=now,
            updated_at=now,
        )
        await self.job_repository.update(updated_job)
        await self._record_job_event(
            job=updated_job,
            event_type="turn.interrupted",
            payload={
                "thread_id": thread_id,
                "turn_id": turn_id,
                "reason": reason,
                "bridge": payload,
            },
            created_at=now,
        )
        await self._record_session_event(
            session_id=session.id,
            event_type="command.interrupt",
            actor_type="agent",
            actor_id=agent.id,
            payload={
                "job_id": updated_job.id,
                "thread_id": thread_id,
                "turn_id": turn_id,
                "reason": reason,
            },
            created_at=now,
        )
        return RelayExecutionResult(
            job_id=updated_job.id,
            session_id=updated_job.session_id,
            agent_id=updated_job.assigned_agent_id,
            thread_id=thread_id,
            turn_id=turn_id,
            message_id=None,
            event_type="turn.interrupted",
        )

    async def compact_job(
        self,
        job_id: str,
        *,
        reason: str | None = None,
    ) -> RelayExecutionResult:
        """Compact the Codex thread for a job."""
        job = await self._get_job(job_id)
        session = await self._get_session(job.session_id)
        agent = await self._get_agent(job.assigned_agent_id)
        thread_id = job.codex_thread_id
        if thread_id is None:
            mapping = self.thread_mapping_service.store.get(job.session_id, job.assigned_agent_id)
            thread_id = mapping.codex_thread_id if mapping is not None else None
        if thread_id is None:
            raise LookupError(f"No Codex thread mapped for job {job.id}")

        now = _utc_now()
        response = await self.bridge.thread_compact_start(
            {
                "session_id": job.session_id,
                "job_id": job.id,
                "thread_id": thread_id,
                "reason": reason,
            }
        )
        payload = _unwrap_result(response)
        updated_job = replace(
            job,
            last_known_turn_status="compacted",
            updated_at=now,
        )
        await self.job_repository.update(updated_job)
        await self._record_job_event(
            job=updated_job,
            event_type="thread.compact.start",
            payload={"thread_id": thread_id, "reason": reason, "bridge": payload},
            created_at=now,
        )
        await self._record_session_event(
            session_id=session.id,
            event_type="command.compact",
            actor_type="agent",
            actor_id=agent.id,
            payload={
                "job_id": updated_job.id,
                "thread_id": thread_id,
                "reason": reason,
            },
            created_at=now,
        )
        return RelayExecutionResult(
            job_id=updated_job.id,
            session_id=updated_job.session_id,
            agent_id=updated_job.assigned_agent_id,
            thread_id=thread_id,
            turn_id=job.active_turn_id,
            message_id=None,
            event_type="thread.compact.start",
        )

    async def _publish_output_message(
        self,
        *,
        session: SessionRecord,
        job: JobRecord,
        agent: AgentRecord,
        content: str,
        reply_to_message_id: str | None,
        created_at: str,
    ) -> MessageRecord:
        message = MessageRecord(
            id=f"msg_{uuid4().hex}",
            session_id=session.id,
            sender_type="agent",
            sender_id=job.assigned_agent_id,
            message_type="relay",
            content=content,
            content_format="plain_text",
            reply_to_message_id=reply_to_message_id,
            source_message_id=job.source_message_id,
            visibility="session",
            created_at=created_at,
            updated_at=created_at,
        )
        created = await self.message_repository.create(message)
        await self.session_repository.update(
            replace(
                session,
                last_message_at=created_at,
                updated_at=created_at,
            )
        )
        await record_session_event(
            self.session_event_repository,
            session_id=session.id,
            event_type="message.created",
            actor_type="agent",
            actor_id=agent.id,
            payload={
                "message_id": created.id,
                "job_id": job.id,
                "thread_id": job.codex_thread_id,
                "turn_id": job.active_turn_id,
                "message_type": "relay",
            },
            created_at=created_at,
        )
        return created

    async def _record_job_event(
        self,
        *,
        job: JobRecord,
        event_type: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> JobEventRecord:
        event = JobEventRecord(
            id=f"jbe_{uuid4().hex}",
            job_id=job.id,
            session_id=job.session_id,
            event_type=event_type,
            event_payload_json=json.dumps(payload, sort_keys=True),
            created_at=created_at,
        )
        return await self.job_event_repository.create(event)

    async def _record_relay_edge(
        self,
        *,
        job: JobRecord,
        relay_reason: str,
        created_at: str,
    ) -> RelayEdgeRecord:
        edge = RelayEdgeRecord(
            id=f"red_{uuid4().hex}",
            session_id=job.session_id,
            source_message_id=job.source_message_id,
            source_job_id=job.parent_job_id,
            target_agent_id=job.assigned_agent_id,
            target_job_id=job.id,
            relay_reason=relay_reason,
            hop_number=job.hop_count,
            created_at=created_at,
        )
        return await self.relay_edge_repository.create(edge)

    async def _record_session_event(
        self,
        *,
        session_id: str,
        event_type: str,
        actor_type: str | None,
        actor_id: str | None,
        payload: dict[str, Any] | None,
        created_at: str,
    ) -> None:
        await record_session_event(
            self.session_event_repository,
            session_id=session_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload,
            created_at=created_at,
        )

    async def _get_job(self, job_id: str) -> JobRecord:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        return job

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        return session

    async def _get_agent(self, agent_id: str) -> AgentRecord:
        agent = await self.agent_repository.get(agent_id)
        if agent is None:
            raise LookupError(f"Agent not found: {agent_id}")
        return agent
