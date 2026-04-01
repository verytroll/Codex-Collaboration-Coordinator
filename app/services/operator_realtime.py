"""Replayable operator activity feed service."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.models.api.operator_realtime import (
    OperatorActivityCategory,
    OperatorActivitySeverity,
    OperatorActivitySignalResponse,
    OperatorSessionActivityEventResponse,
    OperatorSessionActivityResponse,
    OperatorSessionActivitySignalsResponse,
)
from app.repositories.approvals import ApprovalRepository
from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord, JobRepository
from app.repositories.messages import MessageRecord, MessageRepository
from app.repositories.phases import PhaseRepository
from app.repositories.runtime_pools import RuntimePoolRepository, WorkContextRepository
from app.repositories.session_events import SessionEventRecord, SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.operator_dashboard import OperatorDashboardFilters, OperatorDashboardService

logger = get_logger(__name__)

_BLOCKED_JOB_STATUSES = {"input_required", "auth_required", "paused_by_loop_guard"}
_CRITICAL_EVENT_TYPES = {"loop_guard_triggered", "job.paused_by_loop_guard"}
_WARNING_EVENT_TYPES = {
    "approval.required",
    "approval.declined",
    "review.requested",
    "review.decision.recorded",
    "turn.interrupted",
    "command.interrupt",
}

_EVENT_TITLES: dict[str, str] = {
    "message.created": "Message posted",
    "job.created": "Job queued",
    "job.input_received": "Job input received",
    "job.paused_by_loop_guard": "Job paused by loop guard",
    "turn.started": "Turn started",
    "turn.interrupted": "Turn interrupted",
    "relay.output.published": "Relay output published",
    "command.interrupt": "Interrupt command handled",
    "command.compact": "Compact command handled",
    "thread.compact.start": "Thread compaction started",
    "review.requested": "Review requested",
    "review.decision.recorded": "Review decision recorded",
    "approval.required": "Approval requested",
    "approval.accepted": "Approval accepted",
    "approval.declined": "Approval declined",
    "orchestration.review_requested": "Review gate opened",
    "orchestration.approval_requested": "Approval gate opened",
    "orchestration.review.approved": "Review gate resolved",
    "orchestration.review.rejected": "Review gate rejected",
    "orchestration.approval.accepted": "Approval gate resolved",
    "orchestration.approval.declined": "Approval gate rejected",
    "participant.added": "Participant joined",
    "participant.updated": "Participant updated",
    "participant.removed": "Participant removed",
    "loop_guard_triggered": "Loop guard triggered",
    "recovery.thread_rehydrated": "Thread rehydrated",
    "phase.active": "Active phase snapshot",
}

_EVENT_CATEGORIES: dict[str, OperatorActivityCategory] = {
    "message.created": "message",
    "job.created": "job",
    "job.input_received": "job",
    "job.paused_by_loop_guard": "runtime",
    "turn.started": "job",
    "turn.interrupted": "job",
    "relay.output.published": "job",
    "command.interrupt": "job",
    "command.compact": "job",
    "thread.compact.start": "job",
    "review.requested": "review",
    "review.decision.recorded": "review",
    "approval.required": "approval",
    "approval.accepted": "approval",
    "approval.declined": "approval",
    "orchestration.review_requested": "phase",
    "orchestration.approval_requested": "phase",
    "orchestration.review.approved": "phase",
    "orchestration.review.rejected": "phase",
    "orchestration.approval.accepted": "phase",
    "orchestration.approval.declined": "phase",
    "participant.added": "participant",
    "participant.updated": "participant",
    "participant.removed": "participant",
    "loop_guard_triggered": "runtime",
    "recovery.thread_rehydrated": "runtime",
    "phase.active": "phase",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_json(payload: str | None) -> dict[str, Any]:
    if payload is None:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload}
    return data if isinstance(data, dict) else {"value": data}


def _sort_key(
    created_at: str, source_rank: int, entity_id: str, event_type: str
) -> tuple[str, int, str, str]:
    return (created_at, source_rank, entity_id, event_type)


@dataclass(frozen=True, slots=True)
class _ActivityDraft:
    sort_key: tuple[str, int, str, str]
    event_type: str
    category: OperatorActivityCategory
    severity: OperatorActivitySeverity
    title: str
    detail: str | None
    session_id: str
    entity_type: str
    entity_id: str
    job_id: str | None = None
    phase_key: str | None = None
    runtime_pool_key: str | None = None
    approval_id: str | None = None
    message_id: str | None = None
    actor_type: str | None = None
    actor_id: str | None = None
    payload: dict[str, Any] | None = None
    created_at: str = ""


class OperatorRealtimeService:
    """Build a replayable operator activity feed for a session."""

    def __init__(
        self,
        *,
        dashboard_service: OperatorDashboardService,
        session_repository: SessionRepository,
        phase_repository: PhaseRepository,
        job_repository: JobRepository,
        job_event_repository: JobEventRepository,
        approval_repository: ApprovalRepository,
        message_repository: MessageRepository,
        session_event_repository: SessionEventRepository,
        runtime_pool_repository: RuntimePoolRepository,
        work_context_repository: WorkContextRepository,
    ) -> None:
        self.dashboard_service = dashboard_service
        self.session_repository = session_repository
        self.phase_repository = phase_repository
        self.job_repository = job_repository
        self.job_event_repository = job_event_repository
        self.approval_repository = approval_repository
        self.message_repository = message_repository
        self.session_event_repository = session_event_repository
        self.runtime_pool_repository = runtime_pool_repository
        self.work_context_repository = work_context_repository

    async def get_session_activity(
        self,
        *,
        session_id: str,
        since_sequence: int = 0,
        limit: int = 25,
    ) -> OperatorSessionActivityResponse:
        """Return replayable activity for a selected session."""
        if since_sequence < 0:
            raise ValueError("since_sequence must be greater than or equal to 0")
        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1")

        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")

        dashboard = await self.dashboard_service.get_dashboard(
            OperatorDashboardFilters(session_id=session_id)
        )
        jobs_task = self.job_repository.list_by_session(session_id)
        approvals_task = self.approval_repository.list()
        messages_task = self.message_repository.list_by_session(session_id)
        session_events_task = self.session_event_repository.list_by_session(session_id)
        job_events_task = self.job_event_repository.list_by_session(session_id)
        phases_task = self.phase_repository.list_by_session(session_id)
        jobs, approvals, messages, session_events, job_events, phases = await asyncio.gather(
            jobs_task,
            approvals_task,
            messages_task,
            session_events_task,
            job_events_task,
            phases_task,
        )
        session_job_ids = {job.id for job in jobs}
        runtime_pools = await self.runtime_pool_repository.list()
        work_contexts = await self.work_context_repository.list_by_session(session_id)
        runtime_key_by_id = {pool.id: pool.pool_key for pool in runtime_pools}
        active_phase_key = None
        if session.active_phase_id is not None:
            active_phase = next(
                (phase for phase in phases if phase.id == session.active_phase_id), None
            )
            if active_phase is not None:
                active_phase_key = active_phase.phase_key
        job_phase_key_by_id = self._job_phase_key_map(active_phase_key, jobs)
        job_runtime_pool_key_by_id = self._job_runtime_pool_key_map(
            work_contexts,
            runtime_key_by_id,
        )
        drafts = self._build_activity_drafts(
            session_id=session_id,
            jobs=jobs,
            approvals=approvals,
            messages=messages,
            session_events=session_events,
            job_events=job_events,
            job_phase_key_by_id=job_phase_key_by_id,
            job_runtime_pool_key_by_id=job_runtime_pool_key_by_id,
            phases=phases,
            active_phase_id=session.active_phase_id,
        )
        activity_events = self._materialize_events(
            drafts,
            since_sequence=since_sequence,
            limit=limit,
        )
        signals = self._build_signals(
            dashboard=dashboard,
            jobs=jobs,
            approvals=approvals,
            session_events=session_events,
            session_job_ids=session_job_ids,
        )
        logger.info(
            "operator session activity generated",
            extra={
                "session_id": session_id,
                "since_sequence": since_sequence,
                "event_count": len(activity_events),
                "total_events": len(drafts),
            },
        )
        return OperatorSessionActivityResponse(
            session_id=session_id,
            since_sequence=since_sequence,
            next_cursor_sequence=activity_events[-1].sequence
            if activity_events
            else since_sequence,
            total_events=len(drafts),
            generated_at=_utc_now(),
            events=activity_events,
            signals=signals,
        )

    def _build_activity_drafts(
        self,
        *,
        session_id: str,
        jobs: list[JobRecord],
        approvals: list[Any],
        messages: list[MessageRecord],
        session_events: list[SessionEventRecord],
        job_events: list[JobEventRecord],
        job_phase_key_by_id: dict[str, str | None],
        job_runtime_pool_key_by_id: dict[str, str | None],
        phases: list[Any],
        active_phase_id: str | None,
    ) -> list[_ActivityDraft]:
        drafts: list[_ActivityDraft] = []
        drafts.extend(
            self._build_session_event_drafts(
                session_events=session_events,
                job_phase_key_by_id=job_phase_key_by_id,
                job_runtime_pool_key_by_id=job_runtime_pool_key_by_id,
            )
        )
        drafts.extend(
            self._build_job_event_drafts(
                job_events=job_events,
                job_phase_key_by_id=job_phase_key_by_id,
                job_runtime_pool_key_by_id=job_runtime_pool_key_by_id,
            )
        )
        drafts.extend(
            self._build_job_snapshot_drafts(
                session_id=session_id,
                jobs=jobs,
                job_phase_key_by_id=job_phase_key_by_id,
                job_runtime_pool_key_by_id=job_runtime_pool_key_by_id,
            )
        )
        drafts.extend(
            self._build_phase_snapshot_drafts(
                session_id=session_id,
                phases=phases,
                active_phase_id=active_phase_id,
            )
        )
        drafts.extend(self._build_message_snapshot_drafts(messages))
        drafts.sort(key=lambda draft: draft.sort_key)
        return drafts

    def _build_session_event_drafts(
        self,
        *,
        session_events: list[SessionEventRecord],
        job_phase_key_by_id: dict[str, str | None],
        job_runtime_pool_key_by_id: dict[str, str | None],
    ) -> list[_ActivityDraft]:
        drafts: list[_ActivityDraft] = []
        for event in session_events:
            payload = _parse_json(event.event_payload_json)
            job_id = payload.get("job_id") if isinstance(payload.get("job_id"), str) else None
            phase_key = (
                payload.get("phase_key") if isinstance(payload.get("phase_key"), str) else None
            )
            runtime_pool_key = (
                payload.get("runtime_pool_key")
                if isinstance(payload.get("runtime_pool_key"), str)
                else None
            )
            if phase_key is None and job_id is not None:
                phase_key = job_phase_key_by_id.get(job_id)
            if runtime_pool_key is None and job_id is not None:
                runtime_pool_key = job_runtime_pool_key_by_id.get(job_id)
            entity_id = (
                job_id
                or payload.get("approval_id")
                or payload.get("message_id")
                or payload.get("review_id")
                or event.id
            )
            drafts.append(
                _ActivityDraft(
                    sort_key=_sort_key(event.created_at, 0, str(entity_id), event.event_type),
                    event_type=event.event_type,
                    category=self._event_category(event.event_type),
                    severity=self._event_severity(event.event_type, payload),
                    title=self._event_title(event.event_type, payload),
                    detail=self._event_detail(event.event_type, payload),
                    session_id=event.session_id,
                    entity_type=self._entity_type_for_session_event(event.event_type),
                    entity_id=str(entity_id),
                    job_id=job_id,
                    phase_key=phase_key,
                    runtime_pool_key=runtime_pool_key,
                    approval_id=(
                        payload.get("approval_id")
                        if isinstance(payload.get("approval_id"), str)
                        else None
                    ),
                    message_id=(
                        payload.get("message_id")
                        if isinstance(payload.get("message_id"), str)
                        else None
                    ),
                    actor_type=event.actor_type,
                    actor_id=event.actor_id,
                    payload=payload or None,
                    created_at=event.created_at,
                )
            )
        return drafts

    def _build_job_event_drafts(
        self,
        *,
        job_events: list[JobEventRecord],
        job_phase_key_by_id: dict[str, str | None],
        job_runtime_pool_key_by_id: dict[str, str | None],
    ) -> list[_ActivityDraft]:
        drafts: list[_ActivityDraft] = []
        for event in job_events:
            payload = _parse_json(event.event_payload_json)
            drafts.append(
                _ActivityDraft(
                    sort_key=_sort_key(event.created_at, 1, event.job_id, event.event_type),
                    event_type=event.event_type,
                    category=self._event_category(event.event_type),
                    severity=self._event_severity(event.event_type, payload),
                    title=self._event_title(event.event_type, payload),
                    detail=self._event_detail(event.event_type, payload),
                    session_id=event.session_id,
                    entity_type="job_event",
                    entity_id=event.id,
                    job_id=event.job_id,
                    phase_key=job_phase_key_by_id.get(event.job_id),
                    runtime_pool_key=job_runtime_pool_key_by_id.get(event.job_id),
                    payload=payload or None,
                    created_at=event.created_at,
                )
            )
        return drafts

    def _build_job_snapshot_drafts(
        self,
        *,
        session_id: str,
        jobs: list[JobRecord],
        job_phase_key_by_id: dict[str, str | None],
        job_runtime_pool_key_by_id: dict[str, str | None],
    ) -> list[_ActivityDraft]:
        drafts: list[_ActivityDraft] = []
        for job in jobs:
            runtime_pool_key = job_runtime_pool_key_by_id.get(job.id)
            payload = {
                "job_id": job.id,
                "status": job.status,
                "priority": job.priority,
                "runtime_id": job.runtime_id,
                "assigned_agent_id": job.assigned_agent_id,
                "title": job.title,
            }
            detail_bits = [f"status={job.status}", f"agent={job.assigned_agent_id}"]
            if runtime_pool_key is not None:
                detail_bits.append(f"pool={runtime_pool_key}")
            drafts.append(
                _ActivityDraft(
                    sort_key=_sort_key(job.created_at, 2, job.id, "job.created"),
                    event_type="job.created",
                    category="job",
                    severity="info",
                    title="Job queued",
                    detail=f"{job.title} | {' '.join(detail_bits)}",
                    session_id=session_id,
                    entity_type="job",
                    entity_id=job.id,
                    job_id=job.id,
                    phase_key=job_phase_key_by_id.get(job.id),
                    runtime_pool_key=runtime_pool_key,
                    payload=payload,
                    created_at=job.created_at,
                )
            )
        return drafts

    def _build_phase_snapshot_drafts(
        self,
        *,
        session_id: str,
        phases: list[Any],
        active_phase_id: str | None,
    ) -> list[_ActivityDraft]:
        drafts: list[_ActivityDraft] = []
        for phase in phases:
            if phase.id != active_phase_id:
                continue
            payload = {
                "phase_id": phase.id,
                "phase_key": phase.phase_key,
                "phase_title": phase.title,
                "relay_template_key": phase.relay_template_key,
            }
            drafts.append(
                _ActivityDraft(
                    sort_key=_sort_key(phase.updated_at, 3, phase.id, "phase.active"),
                    event_type="phase.active",
                    category="phase",
                    severity="info",
                    title=f"Active phase: {phase.phase_key}",
                    detail=phase.title,
                    session_id=session_id,
                    entity_type="phase",
                    entity_id=phase.id,
                    phase_key=phase.phase_key,
                    payload=payload,
                    created_at=phase.updated_at,
                )
            )
        return drafts

    def _build_message_snapshot_drafts(self, messages: list[MessageRecord]) -> list[_ActivityDraft]:
        drafts: list[_ActivityDraft] = []
        for message in messages:
            payload = {
                "message_id": message.id,
                "sender_type": message.sender_type,
                "sender_id": message.sender_id,
                "channel_key": message.channel_key,
                "message_type": message.message_type,
            }
            detail = message.sender_type
            if message.sender_id is not None:
                detail = f"{detail} | {message.sender_id}"
            detail = f"{detail} | {message.message_type}"
            drafts.append(
                _ActivityDraft(
                    sort_key=_sort_key(message.created_at, 0, message.id, "message.created"),
                    event_type="message.created",
                    category="message",
                    severity="info",
                    title="Message posted",
                    detail=detail,
                    session_id=message.session_id,
                    entity_type="message",
                    entity_id=message.id,
                    message_id=message.id,
                    payload=payload,
                    created_at=message.created_at,
                )
            )
        return drafts

    def _materialize_events(
        self,
        drafts: list[_ActivityDraft],
        *,
        since_sequence: int,
        limit: int,
    ) -> list[OperatorSessionActivityEventResponse]:
        numbered = [
            OperatorSessionActivityEventResponse(
                sequence=index + 1,
                event_type=draft.event_type,
                category=draft.category,
                severity=draft.severity,
                title=draft.title,
                detail=draft.detail,
                session_id=draft.session_id,
                entity_type=draft.entity_type,
                entity_id=draft.entity_id,
                job_id=draft.job_id,
                phase_key=draft.phase_key,
                runtime_pool_key=draft.runtime_pool_key,
                approval_id=draft.approval_id,
                message_id=draft.message_id,
                actor_type=draft.actor_type,
                actor_id=draft.actor_id,
                payload=draft.payload,
                created_at=draft.created_at,
            )
            for index, draft in enumerate(drafts)
        ]
        if since_sequence == 0:
            return numbered[-limit:]
        return [event for event in numbered if event.sequence > since_sequence][:limit]

    def _build_signals(
        self,
        *,
        dashboard: dict[str, Any],
        jobs: list[JobRecord],
        approvals: list[Any],
        session_events: list[SessionEventRecord],
        session_job_ids: set[str],
    ) -> OperatorSessionActivitySignalsResponse:
        return OperatorSessionActivitySignalsResponse(
            pending_approvals=[
                self._approval_signal(approval)
                for approval in approvals
                if getattr(approval, "status", None) == "pending"
                and getattr(approval, "job_id", None) in session_job_ids
            ],
            recent_errors=self._recent_error_signals(jobs=jobs, session_events=session_events),
            stuck_jobs=self._stuck_job_signals(jobs),
            phase_bottlenecks=self._phase_bottleneck_signals(dashboard),
            runtime_health=self._runtime_health_signals(dashboard),
        )

    def _approval_signal(self, approval: Any) -> OperatorActivitySignalResponse:
        return OperatorActivitySignalResponse(
            kind="pending_approval",
            title=f"{approval.approval_type} approval pending",
            detail=f"job={approval.job_id} agent={approval.agent_id}",
            severity="warning",
            entity_type="approval",
            entity_id=approval.id,
            created_at=approval.requested_at,
        )

    def _recent_error_signals(
        self,
        *,
        jobs: list[JobRecord],
        session_events: list[SessionEventRecord],
    ) -> list[OperatorActivitySignalResponse]:
        signals: list[OperatorActivitySignalResponse] = []
        for job in jobs:
            if job.error_message is None and job.status != "failed":
                continue
            signals.append(
                OperatorActivitySignalResponse(
                    kind="recent_error",
                    title=f"Job {job.id} is in error",
                    detail=job.error_message or job.error_code or job.result_summary or job.status,
                    severity="critical" if job.status == "failed" else "warning",
                    entity_type="job",
                    entity_id=job.id,
                    created_at=job.updated_at,
                )
            )
        for event in session_events:
            if event.event_type != "loop_guard_triggered":
                continue
            payload = _parse_json(event.event_payload_json)
            reason = payload.get("reason") if isinstance(payload.get("reason"), str) else None
            signals.append(
                OperatorActivitySignalResponse(
                    kind="recent_error",
                    title="Loop guard triggered",
                    detail=reason or "Loop guard paused relay activity",
                    severity="critical",
                    entity_type="session_event",
                    entity_id=event.id,
                    created_at=event.created_at,
                )
            )
        signals.sort(key=lambda signal: signal.created_at or "", reverse=True)
        return signals[:5]

    def _stuck_job_signals(self, jobs: list[JobRecord]) -> list[OperatorActivitySignalResponse]:
        signals: list[OperatorActivitySignalResponse] = []
        for job in jobs:
            if job.status not in _BLOCKED_JOB_STATUSES:
                continue
            signals.append(
                OperatorActivitySignalResponse(
                    kind="stuck_job",
                    title=job.title,
                    detail=f"status={job.status} agent={job.assigned_agent_id}",
                    severity="critical" if job.status == "paused_by_loop_guard" else "warning",
                    entity_type="job",
                    entity_id=job.id,
                    created_at=job.updated_at,
                )
            )
        signals.sort(key=lambda signal: signal.created_at or "", reverse=True)
        return signals[:5]

    def _phase_bottleneck_signals(
        self, dashboard: dict[str, Any]
    ) -> list[OperatorActivitySignalResponse]:
        signals: list[OperatorActivitySignalResponse] = []
        for item in dashboard.get("phase_distribution", []):
            if not isinstance(item, dict):
                continue
            count = int(
                item.get("blocked_jobs", 0)
                + item.get("pending_reviews", 0)
                + item.get("pending_gates", 0)
            )
            if count <= 0:
                continue
            signals.append(
                OperatorActivitySignalResponse(
                    kind="phase_bottleneck",
                    title=str(item.get("phase_key", "unknown")),
                    detail=(
                        f"{item.get('blocked_jobs', 0)} blocked jobs, "
                        f"{item.get('pending_reviews', 0)} pending reviews, "
                        f"{item.get('pending_gates', 0)} pending gates"
                    ),
                    severity="warning",
                    count=count,
                    entity_type="phase",
                    entity_id=str(item.get("phase_key", "unknown")),
                )
            )
        return signals[:5]

    def _runtime_health_signals(
        self, dashboard: dict[str, Any]
    ) -> list[OperatorActivitySignalResponse]:
        signals: list[OperatorActivitySignalResponse] = []
        for item in dashboard.get("runtime_pools", []):
            if not isinstance(item, dict):
                continue
            pool_status = str(item.get("pool_status", "unknown"))
            pressure = int(
                item.get("queued_jobs", 0)
                + item.get("blocked_jobs", 0)
                + item.get("pending_reviews", 0)
                + item.get("pending_tasks", 0)
            )
            if pool_status == "ready" and pressure == 0:
                continue
            utilization = item.get("utilization_ratio", 0)
            ratio = int(float(utilization or 0) * 100)
            signals.append(
                OperatorActivitySignalResponse(
                    kind="runtime_health",
                    title=str(item.get("pool_key", "unknown")),
                    detail=(
                        f"status={pool_status} util={ratio}% "
                        f"queued={item.get('queued_jobs', 0)} blocked={item.get('blocked_jobs', 0)}"
                    ),
                    severity="critical" if pool_status in {"offline", "crashed"} else "warning",
                    count=pressure,
                    entity_type="runtime_pool",
                    entity_id=str(item.get("pool_key", "unknown")),
                    created_at=str(item.get("updated_at")) if item.get("updated_at") else None,
                )
            )
        return signals[:5]

    def _event_category(self, event_type: str) -> OperatorActivityCategory:
        if event_type in _EVENT_CATEGORIES:
            return _EVENT_CATEGORIES[event_type]
        if event_type.startswith("message."):
            return "message"
        if event_type.startswith("review."):
            return "review"
        if event_type.startswith("approval."):
            return "approval"
        if event_type.startswith("participant."):
            return "participant"
        if event_type.startswith("orchestration.") or event_type.startswith("phase."):
            return "phase"
        if event_type.startswith("loop_guard") or event_type.startswith("recovery."):
            return "runtime"
        return "system"

    def _event_severity(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> OperatorActivitySeverity:
        if event_type in _CRITICAL_EVENT_TYPES:
            return "critical"
        if event_type in _WARNING_EVENT_TYPES:
            return "warning"
        if event_type == "review.decision.recorded" and payload.get("decision") in {
            "changes_requested",
            "declined",
        }:
            return "warning"
        if event_type == "orchestration.review.rejected":
            return "warning"
        return "info"

    def _event_title(self, event_type: str, payload: dict[str, Any]) -> str:
        if event_type == "phase.active" and isinstance(payload.get("phase_key"), str):
            return f"Active phase: {payload['phase_key']}"
        return _EVENT_TITLES.get(event_type, event_type.replace("_", " ").title())

    def _event_detail(self, event_type: str, payload: dict[str, Any]) -> str | None:
        if event_type == "message.created":
            sender_type = payload.get("sender_type")
            sender_id = payload.get("sender_id")
            channel_key = payload.get("channel_key")
            parts = [str(sender_type) if sender_type is not None else "message"]
            if sender_id is not None:
                parts.append(str(sender_id))
            if channel_key is not None:
                parts.append(f"#{channel_key}")
            return " | ".join(parts)
        if event_type == "job.created":
            return str(payload.get("title") or payload.get("status") or "Queued job")
        if event_type in {"approval.required", "approval.accepted", "approval.declined"}:
            return f"approval_id={payload.get('approval_id')}"
        if event_type.startswith("review."):
            review_id = payload.get("review_id")
            if isinstance(review_id, str):
                return f"review_id={review_id}"
        if event_type.startswith("orchestration."):
            summary = ", ".join(
                f"{key}={value}"
                for key, value in payload.items()
                if key in {"run_id", "source_job_id", "handoff_job_id", "resolved_phase_key"}
                and value is not None
            )
            return summary or None
        if event_type == "loop_guard_triggered" and isinstance(payload.get("reason"), str):
            return str(payload["reason"])
        if event_type == "recovery.thread_rehydrated" and isinstance(payload.get("thread_id"), str):
            return f"thread_id={payload['thread_id']}"
        if event_type == "phase.active" and isinstance(payload.get("phase_title"), str):
            return str(payload["phase_title"])
        return None

    def _entity_type_for_session_event(self, event_type: str) -> str:
        if event_type.startswith("message."):
            return "message"
        if event_type.startswith("review."):
            return "review"
        if event_type.startswith("approval."):
            return "approval"
        if event_type.startswith("participant."):
            return "participant"
        if event_type.startswith("orchestration."):
            return "orchestration"
        if event_type.startswith("recovery.") or event_type.startswith("loop_guard"):
            return "runtime"
        return "session_event"

    def _job_phase_key_map(
        self,
        active_phase_key: str | None,
        jobs: list[JobRecord],
    ) -> dict[str, str | None]:
        return {job.id: active_phase_key for job in jobs}

    def _job_runtime_pool_key_map(
        self,
        work_contexts: list[Any],
        runtime_key_by_id: dict[str, str],
    ) -> dict[str, str | None]:
        return {
            context.job_id: runtime_key_by_id.get(context.runtime_pool_id)
            for context in work_contexts
        }
