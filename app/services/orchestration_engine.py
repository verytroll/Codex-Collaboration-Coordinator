"""Orchestration run state management."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.orchestration_runs import (
    OrchestrationRunRecord,
    OrchestrationRunRepository,
)
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.phase_service import PhaseService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class OrchestrationRunResult:
    """Result from starting or syncing an orchestration run."""

    run: OrchestrationRunRecord


class OrchestrationEngineService:
    """Persist orchestration state for a session."""

    def __init__(
        self,
        *,
        orchestration_run_repository: OrchestrationRunRepository,
        session_repository: SessionRepository,
        phase_service: PhaseService,
    ) -> None:
        self.orchestration_run_repository = orchestration_run_repository
        self.session_repository = session_repository
        self.phase_service = phase_service

    async def list_runs(self) -> list[OrchestrationRunRecord]:
        """Return all orchestration runs."""
        return await self.orchestration_run_repository.list()

    async def get_run(self, run_id: str) -> OrchestrationRunRecord | None:
        """Return a run by id."""
        return await self.orchestration_run_repository.get(run_id)

    async def get_run_by_session(self, session_id: str) -> OrchestrationRunRecord | None:
        """Return the orchestration run for a session."""
        return await self.orchestration_run_repository.get_by_session(session_id)

    async def get_run_by_review_id(self, review_id: str) -> OrchestrationRunRecord | None:
        """Return the orchestration run for a review."""
        return await self.orchestration_run_repository.get_by_review_id(review_id)

    async def get_run_by_approval_id(self, approval_id: str) -> OrchestrationRunRecord | None:
        """Return the orchestration run for an approval."""
        return await self.orchestration_run_repository.get_by_approval_id(approval_id)

    async def start_run(self, session_id: str) -> OrchestrationRunResult:
        """Create or sync the orchestration run for a session."""
        session = await self._get_session(session_id)
        phase = await self.phase_service.get_active_phase(session_id)
        if phase is None:
            raise LookupError(f"No active phase found for session {session_id}")

        existing = await self.orchestration_run_repository.get_by_session(session_id)
        now = _utc_now()
        if existing is None:
            created = await self.orchestration_run_repository.create(
                OrchestrationRunRecord(
                    id=f"orn_{uuid4().hex}",
                    session_id=session.id,
                    status="active",
                    current_phase_id=phase.id,
                    current_phase_key=phase.phase_key,
                    pending_phase_key=None,
                    failure_phase_key="revise",
                    gate_type=None,
                    gate_status="idle",
                    source_job_id=None,
                    handoff_job_id=None,
                    review_id=None,
                    approval_id=None,
                    transition_artifact_id=None,
                    decision_artifact_id=None,
                    revision_job_id=None,
                    requested_by_agent_id=None,
                    transition_reason=None,
                    started_at=now,
                    decided_at=None,
                    completed_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            return OrchestrationRunResult(run=created)

        if existing.gate_status == "pending":
            return OrchestrationRunResult(run=existing)

        updated = replace(
            existing,
            status="active",
            current_phase_id=phase.id,
            current_phase_key=phase.phase_key,
            pending_phase_key=None,
            failure_phase_key=existing.failure_phase_key or "revise",
            gate_type=None,
            gate_status="idle",
            source_job_id=None,
            handoff_job_id=None,
            review_id=None,
            approval_id=None,
            transition_artifact_id=None,
            decision_artifact_id=None,
            revision_job_id=None,
            requested_by_agent_id=None,
            transition_reason=None,
            started_at=existing.started_at or now,
            decided_at=None,
            completed_at=None,
            updated_at=now,
        )
        saved = await self.orchestration_run_repository.update(updated)
        return OrchestrationRunResult(run=saved)

    async def record_gate_request(
        self,
        *,
        session_id: str,
        gate_type: str,
        success_phase_key: str,
        failure_phase_key: str,
        source_job_id: str,
        handoff_job_id: str | None,
        review_id: str | None = None,
        approval_id: str | None = None,
        transition_artifact_id: str | None = None,
        requested_by_agent_id: str | None = None,
        transition_reason: str | None = None,
    ) -> OrchestrationRunResult:
        """Persist a pending gate request."""
        run_result = await self.start_run(session_id)
        run = run_result.run
        if self._matches_pending_gate(
            run,
            gate_type=gate_type,
            source_job_id=source_job_id,
            success_phase_key=success_phase_key,
            failure_phase_key=failure_phase_key,
        ):
            return run_result
        now = _utc_now()
        updated = replace(
            run,
            status="blocked",
            pending_phase_key=success_phase_key,
            failure_phase_key=failure_phase_key,
            gate_type=gate_type,
            gate_status="pending",
            source_job_id=source_job_id,
            handoff_job_id=handoff_job_id,
            review_id=review_id,
            approval_id=approval_id,
            transition_artifact_id=transition_artifact_id,
            requested_by_agent_id=requested_by_agent_id,
            transition_reason=transition_reason,
            decided_at=None,
            updated_at=now,
        )
        saved = await self.orchestration_run_repository.update(updated)
        return OrchestrationRunResult(run=saved)

    async def record_gate_resolution(
        self,
        *,
        run: OrchestrationRunRecord,
        resolved_phase_id: str,
        resolved_phase_key: str,
        gate_status: str,
        decision_artifact_id: str,
        revision_job_id: str | None = None,
        completed: bool = False,
    ) -> OrchestrationRunResult:
        """Persist a resolved gate decision."""
        if self._matches_resolved_gate(
            run,
            resolved_phase_id=resolved_phase_id,
            resolved_phase_key=resolved_phase_key,
            gate_status=gate_status,
            decision_artifact_id=decision_artifact_id,
            revision_job_id=revision_job_id,
            completed=completed,
        ):
            return OrchestrationRunResult(run=run)
        now = _utc_now()
        updated = replace(
            run,
            status="completed" if completed else "active",
            current_phase_id=resolved_phase_id,
            current_phase_key=resolved_phase_key,
            pending_phase_key=None,
            gate_status=gate_status,
            gate_type=run.gate_type,
            decision_artifact_id=decision_artifact_id,
            revision_job_id=revision_job_id,
            decided_at=now,
            completed_at=now if completed else run.completed_at,
            updated_at=now,
        )
        saved = await self.orchestration_run_repository.update(updated)
        return OrchestrationRunResult(run=saved)

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        return session

    @staticmethod
    def _matches_pending_gate(
        run: OrchestrationRunRecord,
        *,
        gate_type: str,
        source_job_id: str,
        success_phase_key: str,
        failure_phase_key: str,
    ) -> bool:
        return (
            run.gate_status == "pending"
            and run.gate_type == gate_type
            and run.source_job_id == source_job_id
            and run.pending_phase_key == success_phase_key
            and run.failure_phase_key == failure_phase_key
        )

    @staticmethod
    def _matches_resolved_gate(
        run: OrchestrationRunRecord,
        *,
        resolved_phase_id: str,
        resolved_phase_key: str,
        gate_status: str,
        decision_artifact_id: str,
        revision_job_id: str | None,
        completed: bool,
    ) -> bool:
        return (
            run.current_phase_id == resolved_phase_id
            and run.current_phase_key == resolved_phase_key
            and run.gate_status == gate_status
            and run.decision_artifact_id == decision_artifact_id
            and run.revision_job_id == revision_job_id
            and ((completed and run.completed_at is not None) or not completed)
        )
