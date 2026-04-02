"""Operator write actions and audit trail helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from app.core.errors import ConflictError, NotFoundError
from app.models.api.operator_actions import (
    OperatorActionKind,
    OperatorActionOutcome,
    OperatorActionTargetType,
)
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.phases import PhaseRecord
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.approval_manager import ApprovalManager
from app.services.offline_queue import OfflineQueueService
from app.services.phase_service import PhaseService
from app.services.relay_engine import RelayEngine
from app.services.session_events import record_session_event

_RETRY_DUPLICATE_MARKER = "retry_requested"
_RESUME_DUPLICATE_MARKER = "resumed"
_TERMINAL_JOB_STATUSES = {"completed", "failed"}
_CANCELABLE_JOB_STATUSES = {
    "queued",
    "running",
    "input_required",
    "auth_required",
    "paused_by_loop_guard",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class OperatorActionAuditRecord:
    """Persisted audit event for an operator action."""

    event_id: str
    event_type: str
    actor_type: str | None
    actor_id: str | None
    session_id: str
    target_type: OperatorActionTargetType
    target_id: str
    result: OperatorActionOutcome
    reason: str | None
    note: str | None
    failure_mode: str | None
    detail: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class OperatorActionResult:
    """Unified operator action result."""

    action: OperatorActionKind
    outcome: OperatorActionOutcome
    session_id: str
    target_type: OperatorActionTargetType
    target_id: str
    target_state_before: str | None
    target_state_after: str | None
    message: str
    audit: OperatorActionAuditRecord
    job: JobRecord | None = None
    approval: ApprovalRequestRecord | None = None
    phase: PhaseRecord | None = None


class OperatorActionService:
    """Execute operator write actions with a session audit trail."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        job_repository: JobRepository,
        approval_repository: ApprovalRepository,
        session_event_repository: SessionEventRepository,
        approval_manager: ApprovalManager,
        offline_queue_service: OfflineQueueService,
        phase_service: PhaseService,
        relay_engine: RelayEngine,
    ) -> None:
        self.session_repository = session_repository
        self.job_repository = job_repository
        self.approval_repository = approval_repository
        self.session_event_repository = session_event_repository
        self.approval_manager = approval_manager
        self.offline_queue_service = offline_queue_service
        self.phase_service = phase_service
        self.relay_engine = relay_engine

    async def approve_approval(
        self,
        approval_id: str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        context: dict[str, object] | None = None,
    ) -> OperatorActionResult:
        """Approve an approval request from the operator surface."""
        approval = await self._get_approval(approval_id)
        job = await self._get_job(approval.job_id)
        before_status = approval.status
        if before_status != "pending":
            await self._record_audit(
                action="approve",
                session_id=job.session_id,
                target_type="approval",
                target_id=approval_id,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="invalid_state",
                detail=f"Approval request already resolved: {approval_id}",
                target_state_before=before_status,
                target_state_after=before_status,
                context=context,
            )
            raise ConflictError(f"Approval request already resolved: {approval_id}")
        decision_payload = self._build_decision_payload(
            actor_id=actor_id,
            reason=reason,
            note=note,
            context=context,
        )
        decision = await self.approval_manager.accept(
            approval_id,
            decision_payload=decision_payload,
        )
        updated_approval = decision.approval
        updated_job = decision.job or await self._get_job(job.id)
        audit = await self._record_audit(
            action="approve",
            session_id=job.session_id,
            target_type="approval",
            target_id=approval_id,
            result="applied",
            actor_id=actor_id,
            reason=reason,
            note=note,
            target_state_before=before_status,
            target_state_after=updated_approval.status,
            context=context,
        )
        return OperatorActionResult(
            action="approve",
            outcome="applied",
            session_id=job.session_id,
            target_type="approval",
            target_id=approval_id,
            target_state_before=before_status,
            target_state_after=updated_approval.status,
            message="Approval accepted",
            audit=audit,
            approval=updated_approval,
            job=updated_job,
        )

    async def reject_approval(
        self,
        approval_id: str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        context: dict[str, object] | None = None,
    ) -> OperatorActionResult:
        """Reject an approval request from the operator surface."""
        approval = await self._get_approval(approval_id)
        job = await self._get_job(approval.job_id)
        before_status = approval.status
        if before_status != "pending":
            await self._record_audit(
                action="reject",
                session_id=job.session_id,
                target_type="approval",
                target_id=approval_id,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="invalid_state",
                detail=f"Approval request already resolved: {approval_id}",
                target_state_before=before_status,
                target_state_after=before_status,
                context=context,
            )
            raise ConflictError(f"Approval request already resolved: {approval_id}")
        decision_payload = self._build_decision_payload(
            actor_id=actor_id,
            reason=reason,
            note=note,
            context=context,
        )
        decision = await self.approval_manager.decline(
            approval_id,
            decision_payload=decision_payload,
        )
        updated_approval = decision.approval
        updated_job = decision.job or await self._get_job(job.id)
        audit = await self._record_audit(
            action="reject",
            session_id=job.session_id,
            target_type="approval",
            target_id=approval_id,
            result="applied",
            actor_id=actor_id,
            reason=reason,
            note=note,
            target_state_before=before_status,
            target_state_after=updated_approval.status,
            context=context,
        )
        return OperatorActionResult(
            action="reject",
            outcome="applied",
            session_id=job.session_id,
            target_type="approval",
            target_id=approval_id,
            target_state_before=before_status,
            target_state_after=updated_approval.status,
            message="Approval rejected",
            audit=audit,
            approval=updated_approval,
            job=updated_job,
        )

    async def retry_job(
        self,
        job_id: str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        context: dict[str, object] | None = None,
    ) -> OperatorActionResult:
        """Retry a job from the operator surface."""
        job = await self._get_job(job_id)
        if job.status == "queued" and job.last_known_turn_status == _RETRY_DUPLICATE_MARKER:
            audit = await self._record_audit(
                action="retry",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                result="duplicate",
                actor_id=actor_id,
                reason=reason,
                note=note,
                target_state_before=job.status,
                target_state_after=job.status,
                context=context,
            )
            return OperatorActionResult(
                action="retry",
                outcome="duplicate",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                target_state_before=job.status,
                target_state_after=job.status,
                message="Retry already requested",
                audit=audit,
                job=job,
            )
        if job.status not in {"failed", "canceled", "paused_by_loop_guard"}:
            await self._record_audit(
                action="retry",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="invalid_state",
                detail=f"Job {job.id} cannot be retried from status {job.status}",
                target_state_before=job.status,
                target_state_after=job.status,
                context=context,
            )
            raise ConflictError(f"Job {job.id} cannot be retried from status {job.status}")
        before_status = job.status
        await self.offline_queue_service.retry_job(job_id, reason=reason)
        updated_job = await self._get_job(job_id)
        audit = await self._record_audit(
            action="retry",
            session_id=job.session_id,
            target_type="job",
            target_id=job.id,
            result="applied",
            actor_id=actor_id,
            reason=reason,
            note=note,
            target_state_before=before_status,
            target_state_after=updated_job.status,
            context=context,
        )
        return OperatorActionResult(
            action="retry",
            outcome="applied",
            session_id=job.session_id,
            target_type="job",
            target_id=job.id,
            target_state_before=before_status,
            target_state_after=updated_job.status,
            message="Job retry recorded",
            audit=audit,
            job=updated_job,
        )

    async def resume_job(
        self,
        job_id: str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        context: dict[str, object] | None = None,
    ) -> OperatorActionResult:
        """Resume a paused job from the operator surface."""
        job = await self._get_job(job_id)
        if job.status == "queued" and job.last_known_turn_status == _RESUME_DUPLICATE_MARKER:
            audit = await self._record_audit(
                action="resume",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                result="duplicate",
                actor_id=actor_id,
                reason=reason,
                note=note,
                target_state_before=job.status,
                target_state_after=job.status,
                context=context,
            )
            return OperatorActionResult(
                action="resume",
                outcome="duplicate",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                target_state_before=job.status,
                target_state_after=job.status,
                message="Resume already requested",
                audit=audit,
                job=job,
            )
        if job.status not in {"queued", "input_required", "auth_required", "paused_by_loop_guard"}:
            await self._record_audit(
                action="resume",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="invalid_state",
                detail=f"Job {job.id} cannot be resumed from status {job.status}",
                target_state_before=job.status,
                target_state_after=job.status,
                context=context,
            )
            raise ConflictError(f"Job {job.id} cannot be resumed from status {job.status}")
        before_status = job.status
        await self.offline_queue_service.resume_job(job_id, reason=reason)
        updated_job = await self._get_job(job_id)
        audit = await self._record_audit(
            action="resume",
            session_id=job.session_id,
            target_type="job",
            target_id=job.id,
            result="applied",
            actor_id=actor_id,
            reason=reason,
            note=note,
            target_state_before=before_status,
            target_state_after=updated_job.status,
            context=context,
        )
        return OperatorActionResult(
            action="resume",
            outcome="applied",
            session_id=job.session_id,
            target_type="job",
            target_id=job.id,
            target_state_before=before_status,
            target_state_after=updated_job.status,
            message="Job resume recorded",
            audit=audit,
            job=updated_job,
        )

    async def cancel_job(
        self,
        job_id: str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        context: dict[str, object] | None = None,
    ) -> OperatorActionResult:
        """Cancel a job from the operator surface."""
        job = await self._get_job(job_id)
        if job.status == "canceled":
            audit = await self._record_audit(
                action="cancel",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                result="duplicate",
                actor_id=actor_id,
                reason=reason,
                note=note,
                target_state_before=job.status,
                target_state_after=job.status,
                context=context,
            )
            return OperatorActionResult(
                action="cancel",
                outcome="duplicate",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                target_state_before=job.status,
                target_state_after=job.status,
                message="Job already canceled",
                audit=audit,
                job=job,
            )
        if job.status in _TERMINAL_JOB_STATUSES:
            await self._record_audit(
                action="cancel",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="invalid_state",
                detail=f"Job {job.id} cannot be canceled from status {job.status}",
                target_state_before=job.status,
                target_state_after=job.status,
                context=context,
            )
            raise ConflictError(f"Job {job.id} cannot be canceled from status {job.status}")
        if job.status not in _CANCELABLE_JOB_STATUSES:
            await self._record_audit(
                action="cancel",
                session_id=job.session_id,
                target_type="job",
                target_id=job.id,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="invalid_state",
                detail=f"Job {job.id} cannot be canceled from status {job.status}",
                target_state_before=job.status,
                target_state_after=job.status,
                context=context,
            )
            raise ConflictError(f"Job {job.id} cannot be canceled from status {job.status}")
        before_status = job.status
        updated_job = job
        if job.status == "running":
            try:
                await self.relay_engine.interrupt_job(job_id, reason=reason or note)
                updated_job = await self._get_job(job_id)
            except LookupError:
                updated_job = await self._cancel_job_directly(job)
        else:
            updated_job = await self._cancel_job_directly(job)
        audit = await self._record_audit(
            action="cancel",
            session_id=job.session_id,
            target_type="job",
            target_id=job.id,
            result="applied",
            actor_id=actor_id,
            reason=reason,
            note=note,
            target_state_before=before_status,
            target_state_after=updated_job.status,
            context=context,
        )
        return OperatorActionResult(
            action="cancel",
            outcome="applied",
            session_id=job.session_id,
            target_type="job",
            target_id=job.id,
            target_state_before=before_status,
            target_state_after=updated_job.status,
            message="Job canceled",
            audit=audit,
            job=updated_job,
        )

    async def activate_phase(
        self,
        session_id: str,
        phase_key: str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        context: dict[str, object] | None = None,
    ) -> OperatorActionResult:
        """Activate a phase for a session from the operator surface."""
        session = await self._get_session(session_id)
        if session.status != "active":
            await self._record_audit(
                action="activate_phase",
                session_id=session_id,
                target_type="phase",
                target_id=phase_key,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="inactive_session",
                detail=f"Session {session.id} is not active",
                target_state_before=session.status,
                target_state_after=session.status,
                context=context,
            )
            raise ConflictError(f"Session {session.id} is not active")
        await self.phase_service.ensure_default_phases(session_id)
        phase = await self.phase_service.get_phase_by_key(session_id, phase_key)
        if phase is None:
            await self._record_audit(
                action="activate_phase",
                session_id=session_id,
                target_type="phase",
                target_id=phase_key,
                result="failed",
                actor_id=actor_id,
                reason=reason,
                note=note,
                failure_mode="missing_phase",
                detail=f"Phase not found in session {session_id}: {phase_key}",
                target_state_before=await self._current_phase_key(session),
                target_state_after=await self._current_phase_key(session),
                context=context,
            )
            raise NotFoundError(f"Phase not found in session {session_id}: {phase_key}")
        before_phase = await self._current_phase_key(session)
        if before_phase == phase.phase_key:
            audit = await self._record_audit(
                action="activate_phase",
                session_id=session_id,
                target_type="phase",
                target_id=phase.id,
                result="duplicate",
                actor_id=actor_id,
                reason=reason,
                note=note,
                target_state_before=before_phase,
                target_state_after=before_phase,
                context=context,
            )
            return OperatorActionResult(
                action="activate_phase",
                outcome="duplicate",
                session_id=session_id,
                target_type="phase",
                target_id=phase.id,
                target_state_before=before_phase,
                target_state_after=before_phase,
                message=f"Phase {phase.phase_key} is already active",
                audit=audit,
                phase=phase,
            )
        result = await self.phase_service.activate_phase_by_key(session_id, phase_key)
        audit = await self._record_audit(
            action="activate_phase",
            session_id=session_id,
            target_type="phase",
            target_id=result.phase.id,
            result="applied",
            actor_id=actor_id,
            reason=reason,
            note=note,
            target_state_before=before_phase,
            target_state_after=result.phase.phase_key,
            context=context,
        )
        return OperatorActionResult(
            action="activate_phase",
            outcome="applied",
            session_id=session_id,
            target_type="phase",
            target_id=result.phase.id,
            target_state_before=before_phase,
            target_state_after=result.phase.phase_key,
            message=f"Phase {result.phase.phase_key} activated",
            audit=audit,
            phase=result.phase,
        )

    async def _record_audit(
        self,
        *,
        action: OperatorActionKind,
        session_id: str,
        target_type: OperatorActionTargetType,
        target_id: str,
        result: OperatorActionOutcome,
        actor_id: str | None,
        reason: str | None,
        note: str | None,
        failure_mode: str | None = None,
        detail: str | None = None,
        target_state_before: str | None = None,
        target_state_after: str | None = None,
        context: dict[str, object] | None = None,
    ) -> OperatorActionAuditRecord:
        event_type = f"operator.action.{action}"
        event = await record_session_event(
            self.session_event_repository,
            session_id=session_id,
            event_type=event_type,
            actor_type="operator",
            actor_id=actor_id,
            payload={
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "result": result,
                "reason": reason,
                "note": note,
                "failure_mode": failure_mode,
                "detail": detail,
                "target_state_before": target_state_before,
                "target_state_after": target_state_after,
                "context": context,
            },
        )
        return OperatorActionAuditRecord(
            event_id=event.id,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            session_id=event.session_id,
            target_type=target_type,
            target_id=target_id,
            result=result,
            reason=reason,
            note=note,
            failure_mode=failure_mode,
            detail=detail,
            created_at=event.created_at,
        )

    @staticmethod
    def _build_decision_payload(
        *,
        actor_id: str | None,
        reason: str | None,
        note: str | None,
        context: dict[str, object] | None,
    ) -> dict[str, object] | None:
        payload: dict[str, object] = {}
        if actor_id is not None:
            payload["actor_id"] = actor_id
        if reason is not None:
            payload["reason"] = reason
        if note is not None:
            payload["note"] = note
        if context is not None:
            payload["context"] = context
        return payload or None

    async def _cancel_job_directly(
        self,
        job: JobRecord,
    ) -> JobRecord:
        now = _utc_now()
        updated = replace(
            job,
            status="canceled",
            last_known_turn_status="operator_canceled",
            completed_at=now,
            updated_at=now,
        )
        return await self.job_repository.update(updated)

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise NotFoundError(f"Session not found: {session_id}")
        return session

    async def _get_job(self, job_id: str) -> JobRecord:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise NotFoundError(f"Job not found: {job_id}")
        return job

    async def _get_approval(self, approval_id: str) -> ApprovalRequestRecord:
        approval = await self.approval_repository.get(approval_id)
        if approval is None:
            raise NotFoundError(f"Approval request not found: {approval_id}")
        return approval

    async def _current_phase_key(self, session: SessionRecord) -> str | None:
        if session.active_phase_id is None:
            return None
        phase = await self.phase_service.get_phase(session.active_phase_id)
        return phase.phase_key if phase is not None else None
