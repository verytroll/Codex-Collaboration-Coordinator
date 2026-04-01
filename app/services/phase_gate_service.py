"""Phase gate orchestration for review and approval transitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.artifacts import ArtifactRecord
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.orchestration_runs import OrchestrationRunRecord
from app.repositories.participants import ParticipantRepository
from app.repositories.reviews import ReviewRecord
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.approval_manager import ApprovalDecision, ApprovalManager
from app.services.artifact_manager import ArtifactManager
from app.services.channel_service import ChannelService
from app.services.job_service import JobService
from app.services.orchestration_engine import (
    OrchestrationEngineService,
    OrchestrationRunResult,
)
from app.services.phase_service import PhaseRecord, PhaseService
from app.services.policy_engine_v2 import PolicyEngineV2Service, PolicyEvaluationResult
from app.services.relay_templates import RelayTemplatesService
from app.services.review_mode import (
    ReviewDecisionResult,
    ReviewModeService,
)
from app.services.session_events import record_session_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class GateRequestResult:
    """Result from opening a gated transition."""

    run: OrchestrationRunRecord
    source_job: JobRecord
    handoff_job: JobRecord | None
    transition_artifact: ArtifactRecord
    review: ReviewRecord | None = None
    approval_id: str | None = None


@dataclass(frozen=True, slots=True)
class GateResolutionResult:
    """Result from resolving a gated transition."""

    run: OrchestrationRunRecord
    resolved_phase: PhaseRecord
    decision_artifact: ArtifactRecord
    revision_job: JobRecord | None


class PhaseGateService:
    """Create and resolve orchestration gates."""

    def __init__(
        self,
        *,
        orchestration_engine_service: OrchestrationEngineService,
        review_mode_service: ReviewModeService,
        approval_manager: ApprovalManager,
        policy_engine_v2_service: PolicyEngineV2Service,
        job_service: JobService,
        artifact_manager: ArtifactManager,
        session_repository: SessionRepository,
        job_repository: JobRepository,
        participant_repository: ParticipantRepository,
        channel_service: ChannelService,
        phase_service: PhaseService,
        relay_templates_service: RelayTemplatesService,
        session_event_repository: SessionEventRepository,
    ) -> None:
        self.orchestration_engine_service = orchestration_engine_service
        self.review_mode_service = review_mode_service
        self.approval_manager = approval_manager
        self.policy_engine_v2_service = policy_engine_v2_service
        self.job_service = job_service
        self.artifact_manager = artifact_manager
        self.session_repository = session_repository
        self.job_repository = job_repository
        self.participant_repository = participant_repository
        self.channel_service = channel_service
        self.phase_service = phase_service
        self.relay_templates_service = relay_templates_service
        self.session_event_repository = session_event_repository

    async def start_run(self, session_id: str) -> OrchestrationRunResult:
        """Start or sync the orchestration run for a session."""
        return await self.orchestration_engine_service.start_run(session_id)

    async def get_run(self, session_id: str) -> OrchestrationRunRecord | None:
        """Return the orchestration run for a session."""
        return await self.orchestration_engine_service.get_run_by_session(session_id)

    async def request_review_gate(
        self,
        *,
        session_id: str,
        source_job_id: str,
        reviewer_agent_id: str | None = None,
        requested_by_agent_id: str | None = None,
        success_phase_key: str = "finalize",
        failure_phase_key: str = "revise",
        notes: str | None = None,
        policy_metadata: dict[str, object] | None = None,
    ) -> GateRequestResult:
        """Open a review-required transition."""
        session = await self._get_session(session_id)
        source_job = await self._get_job(source_job_id)
        if source_job.session_id != session.id:
            raise LookupError(f"Job {source_job.id} does not belong to session {session.id}")
        await self.start_run(session_id)
        review_result = await self.review_mode_service.request_review(
            source_job_id=source_job.id,
            reviewer_agent_id=reviewer_agent_id,
            requested_by_agent_id=requested_by_agent_id,
            review_scope="job",
            review_channel_key="review",
            notes=notes,
            policy_metadata=policy_metadata,
        )
        handoff_job = await self.job_service.create_job_for_agent(
            session_id=session.id,
            agent_id=review_result.review.reviewer_agent_id,
            title=f"Review: {source_job.title}",
            instructions=review_result.request_message.content,
            channel_key=review_result.review.review_channel_key,
            priority=source_job.priority,
            source_message_id=review_result.review.request_message_id,
            parent_job_id=source_job.id,
        )
        transition_artifact = await self.artifact_manager.create_structured_artifact(
            job=source_job,
            artifact_type="json",
            title=f"Review gate for {source_job.title}",
            content_text=json.dumps(
                {
                    "gate_type": "review_required",
                    "source_job_id": source_job.id,
                    "handoff_job_id": handoff_job.id,
                    "review_id": review_result.review.id,
                    "success_phase_key": success_phase_key,
                    "failure_phase_key": failure_phase_key,
                    "review_channel_key": review_result.review.review_channel_key,
                    "policy_metadata": policy_metadata,
                },
                sort_keys=True,
            ),
            file_name=f"{source_job.id}-review-gate.json",
            mime_type="application/json",
            metadata={
                "gate_type": "review_required",
                "review_id": review_result.review.id,
                "handoff_job_id": handoff_job.id,
                "success_phase_key": success_phase_key,
                "failure_phase_key": failure_phase_key,
                "policy_metadata": policy_metadata,
            },
            source_message_id=review_result.review.request_message_id,
            channel_key=review_result.review.review_channel_key,
        )
        run_result = await self.orchestration_engine_service.record_gate_request(
            session_id=session_id,
            gate_type="review_required",
            success_phase_key=success_phase_key,
            failure_phase_key=failure_phase_key,
            source_job_id=source_job.id,
            handoff_job_id=handoff_job.id,
            review_id=review_result.review.id,
            transition_artifact_id=transition_artifact.id,
            requested_by_agent_id=requested_by_agent_id,
            transition_reason=notes,
        )
        await self._record_session_event(
            session_id=session_id,
            event_type="orchestration.review_requested",
            actor_type="agent" if requested_by_agent_id is not None else "system",
            actor_id=requested_by_agent_id,
            payload={
                "run_id": run_result.run.id,
                "source_job_id": source_job.id,
                "review_id": review_result.review.id,
                "handoff_job_id": handoff_job.id,
                "transition_artifact_id": transition_artifact.id,
                "success_phase_key": success_phase_key,
                "failure_phase_key": failure_phase_key,
                "policy_metadata": policy_metadata,
            },
            created_at=_utc_now(),
        )
        return GateRequestResult(
            run=run_result.run,
            source_job=source_job,
            handoff_job=handoff_job,
            transition_artifact=transition_artifact,
            review=review_result.review,
        )

    async def request_approval_gate(
        self,
        *,
        session_id: str,
        source_job_id: str,
        approver_agent_id: str | None = None,
        requested_by_agent_id: str | None = None,
        success_phase_key: str = "finalize",
        failure_phase_key: str = "revise",
        notes: str | None = None,
    ) -> GateRequestResult:
        """Open an approval-required transition."""
        session = await self._get_session(session_id)
        source_job = await self._get_job(source_job_id)
        if source_job.session_id != session.id:
            raise LookupError(f"Job {source_job.id} does not belong to session {session.id}")
        await self.start_run(session_id)
        target_phase = await self._get_phase(session_id, success_phase_key)
        await self.channel_service.ensure_channel_exists(
            session_id=session_id,
            channel_key=target_phase.default_channel_key,
        )
        assigned_agent_id = await self._resolve_approver_agent(
            session=session,
            source_job=source_job,
            explicit_approver_agent_id=approver_agent_id,
        )
        policy_result = await self.policy_engine_v2_service.evaluate_approval_gate(
            session_id=session.id,
            source_job_id=source_job.id,
            success_phase_key=success_phase_key,
            failure_phase_key=failure_phase_key,
            approval_type="custom",
            requested_by_agent_id=requested_by_agent_id,
            approver_agent_id=assigned_agent_id,
            notes=notes,
        )
        policy_metadata = self._policy_metadata(policy_result)
        if policy_result.decision == "escalate_review":
            return await self.request_review_gate(
                session_id=session_id,
                source_job_id=source_job_id,
                reviewer_agent_id=assigned_agent_id,
                requested_by_agent_id=requested_by_agent_id,
                success_phase_key=success_phase_key,
                failure_phase_key=failure_phase_key,
                notes=notes,
                policy_metadata=policy_metadata,
            )
        instructions = self._build_approval_instructions(
            source_job=source_job,
            target_phase=target_phase,
            notes=notes,
        )
        handoff_job = await self.job_service.create_job_for_agent(
            session_id=session.id,
            agent_id=assigned_agent_id,
            title=f"Approve: {source_job.title}",
            instructions=instructions,
            channel_key=target_phase.default_channel_key,
            priority=source_job.priority,
            source_message_id=source_job.source_message_id,
            parent_job_id=source_job.id,
        )
        approval = await self.approval_manager.create_request(
            job=handoff_job,
            approval_type="custom",
            request_payload={
                "gate_type": "approval_required",
                "source_job_id": source_job.id,
                "handoff_job_id": handoff_job.id,
                "success_phase_key": success_phase_key,
                "failure_phase_key": failure_phase_key,
                "notes": notes,
            },
            policy_metadata=policy_metadata,
        )
        resolved = None
        transition_artifact = await self.artifact_manager.create_structured_artifact(
            job=source_job,
            artifact_type="json",
            title=f"Approval gate for {source_job.title}",
            content_text=json.dumps(
                {
                    "gate_type": "approval_required",
                    "source_job_id": source_job.id,
                    "handoff_job_id": handoff_job.id,
                    "approval_id": approval.id,
                    "success_phase_key": success_phase_key,
                    "failure_phase_key": failure_phase_key,
                    "notes": notes,
                    "policy_metadata": policy_metadata,
                },
                sort_keys=True,
            ),
            file_name=f"{source_job.id}-approval-gate.json",
            mime_type="application/json",
            metadata={
                "gate_type": "approval_required",
                "approval_id": approval.id,
                "handoff_job_id": handoff_job.id,
                "success_phase_key": success_phase_key,
                "failure_phase_key": failure_phase_key,
                "policy_metadata": policy_metadata,
            },
            source_message_id=source_job.source_message_id,
            channel_key=target_phase.default_channel_key,
        )
        run_result = await self.orchestration_engine_service.record_gate_request(
            session_id=session_id,
            gate_type="approval_required",
            success_phase_key=success_phase_key,
            failure_phase_key=failure_phase_key,
            source_job_id=source_job.id,
            handoff_job_id=handoff_job.id,
            approval_id=approval.id,
            transition_artifact_id=transition_artifact.id,
            requested_by_agent_id=requested_by_agent_id,
            transition_reason=notes,
        )
        if policy_result.decision == "auto_approve":
            approval_decision = await self.approval_manager.accept(
                approval.id,
                decision_payload={
                    "policy_metadata": policy_metadata,
                    "auto_approved": True,
                },
            )
            resolved = await self.resolve_approval_decision(
                approval_decision,
                decision_payload={
                    "policy_metadata": policy_metadata,
                    "auto_approved": True,
                },
            )
        if resolved is not None:
            run_result = resolved
        await self._record_session_event(
            session_id=session_id,
            event_type="orchestration.approval_requested",
            actor_type="agent" if requested_by_agent_id is not None else "system",
            actor_id=requested_by_agent_id,
            payload={
                "run_id": run_result.run.id,
                "source_job_id": source_job.id,
                "approval_id": approval.id,
                "handoff_job_id": handoff_job.id,
                "transition_artifact_id": transition_artifact.id,
                "success_phase_key": success_phase_key,
                "failure_phase_key": failure_phase_key,
                "policy_metadata": policy_metadata,
            },
            created_at=_utc_now(),
        )
        return GateRequestResult(
            run=run_result.run,
            source_job=source_job,
            handoff_job=handoff_job,
            transition_artifact=transition_artifact,
            approval_id=approval.id,
        )

    async def resolve_review_decision(
        self,
        result: ReviewDecisionResult,
    ) -> GateResolutionResult | None:
        """Resolve the orchestration run associated with a review decision."""
        run = await self.orchestration_engine_service.get_run_by_review_id(result.review.id)
        if run is None:
            return None
        session = await self._get_session(result.review.session_id)
        decision = result.review.review_status
        if decision not in {"approved", "changes_requested"}:
            return None
        resolved_phase_key = (
            run.pending_phase_key if decision == "approved" else run.failure_phase_key
        )
        if resolved_phase_key is None:
            resolved_phase_key = "finalize" if decision == "approved" else "revise"
        phase_result = await self.phase_service.activate_phase_by_key(
            session.id,
            resolved_phase_key,
        )
        updated_run = await self.orchestration_engine_service.record_gate_resolution(
            run=run,
            resolved_phase_id=phase_result.phase.id,
            resolved_phase_key=phase_result.phase.phase_key,
            gate_status="approved" if decision == "approved" else "rejected",
            decision_artifact_id=result.summary_artifact.id,
            revision_job_id=result.revision_job.id if result.revision_job is not None else None,
            completed=resolved_phase_key == "finalize" and decision == "approved",
        )
        await self._record_session_event(
            session_id=session.id,
            event_type=(
                "orchestration.review.approved"
                if decision == "approved"
                else "orchestration.review.rejected"
            ),
            actor_type="agent",
            actor_id=result.review.reviewer_agent_id,
            payload={
                "run_id": updated_run.run.id,
                "review_id": result.review.id,
                "decision_artifact_id": result.summary_artifact.id,
                "revision_job_id": result.revision_job.id
                if result.revision_job is not None
                else None,
                "resolved_phase_key": phase_result.phase.phase_key,
            },
            created_at=_utc_now(),
        )
        return GateResolutionResult(
            run=updated_run.run,
            resolved_phase=phase_result.phase,
            decision_artifact=result.summary_artifact,
            revision_job=result.revision_job,
        )

    async def resolve_approval_decision(
        self,
        approval_decision: ApprovalDecision,
        *,
        decision_payload: dict[str, object] | None = None,
    ) -> GateResolutionResult | None:
        """Resolve the orchestration run associated with an approval decision."""
        run = await self.orchestration_engine_service.get_run_by_approval_id(
            approval_decision.approval.id
        )
        if run is None:
            return None
        approval = approval_decision.approval
        decision = approval.status
        if decision not in {"accepted", "declined"}:
            return None
        source_job = await self._get_job(run.source_job_id or approval.job_id)
        session = await self._get_session(source_job.session_id)
        resolved_phase_key = (
            run.pending_phase_key if decision == "accepted" else run.failure_phase_key
        )
        if resolved_phase_key is None:
            resolved_phase_key = "finalize" if decision == "accepted" else "revise"
        phase_result = await self.phase_service.activate_phase_by_key(
            session.id,
            resolved_phase_key,
        )
        approval_job = approval_decision.job or source_job
        decision_artifact = await self.artifact_manager.create_structured_artifact(
            job=approval_job,
            artifact_type="json",
            title=f"Approval decision for {approval_job.title}",
            content_text=json.dumps(
                {
                    "approval_id": approval.id,
                    "job_id": approval.job_id,
                    "decision": decision,
                    "decision_payload": decision_payload,
                    "resolved_phase_key": resolved_phase_key,
                    "source_job_id": source_job.id,
                },
                sort_keys=True,
            ),
            file_name=f"{approval.id}-decision.json",
            mime_type="application/json",
            metadata={
                "approval_id": approval.id,
                "decision": decision,
                "resolved_phase_key": resolved_phase_key,
                "source_job_id": source_job.id,
            },
            source_message_id=approval_job.source_message_id,
            channel_key=approval_job.channel_key,
        )
        revision_job = None
        if decision == "declined":
            revision_job = await self.job_service.create_job_for_agent(
                session_id=session.id,
                agent_id=source_job.assigned_agent_id,
                title=f"Revise: {source_job.title}",
                instructions=decision_artifact.content_text,
                channel_key=source_job.channel_key,
                priority=source_job.priority,
                source_message_id=source_job.source_message_id,
                parent_job_id=source_job.id,
            )
        updated_run = await self.orchestration_engine_service.record_gate_resolution(
            run=run,
            resolved_phase_id=phase_result.phase.id,
            resolved_phase_key=phase_result.phase.phase_key,
            gate_status="approved" if decision == "accepted" else "rejected",
            decision_artifact_id=decision_artifact.id,
            revision_job_id=revision_job.id if revision_job is not None else None,
            completed=resolved_phase_key == "finalize" and decision == "accepted",
        )
        await self._record_session_event(
            session_id=session.id,
            event_type=f"orchestration.approval.{decision}",
            actor_type="system",
            actor_id=None,
            payload={
                "run_id": updated_run.run.id,
                "approval_id": approval.id,
                "decision_artifact_id": decision_artifact.id,
                "revision_job_id": revision_job.id if revision_job is not None else None,
                "resolved_phase_key": phase_result.phase.phase_key,
            },
            created_at=_utc_now(),
        )
        return GateResolutionResult(
            run=updated_run.run,
            resolved_phase=phase_result.phase,
            decision_artifact=decision_artifact,
            revision_job=revision_job,
        )

    def _build_approval_instructions(
        self,
        *,
        source_job: JobRecord,
        target_phase: PhaseRecord,
        notes: str | None,
    ) -> str:
        lines = [
            f"# Approve transition to {target_phase.title}",
            "",
            f"Source job: `{source_job.id}`",
            f"Source title: {source_job.title}",
            f"Current status: `{source_job.status}`",
            f"Target phase: `{target_phase.phase_key}`",
        ]
        if notes is not None and notes.strip():
            lines.extend(["", notes.strip()])
        lines.extend(
            [
                "",
                "## Metadata",
                f"- source_job_id: `{source_job.id}`",
                f"- target_phase_key: `{target_phase.phase_key}`",
                f"- target_phase_title: `{target_phase.title}`",
            ]
        )
        return "\n".join(lines).strip()

    @staticmethod
    def _policy_metadata(result: PolicyEvaluationResult) -> dict[str, object]:
        return {
            "decision": result.decision,
            "reason": result.reason,
            "policy_id": result.policy.id if result.policy is not None else None,
            "policy_name": result.policy.name if result.policy is not None else None,
            "policy_type": result.policy.policy_type if result.policy is not None else None,
            "decision_record_id": result.decision_record.id,
            "context": result.context,
        }

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        return session

    async def _get_job(self, job_id: str) -> JobRecord:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        return job

    async def _get_phase(self, session_id: str, phase_key: str) -> PhaseRecord:
        phase = await self.phase_service.get_phase_by_key(session_id, phase_key)
        if phase is None:
            raise LookupError(f"Phase not found in session {session_id}: {phase_key}")
        return phase

    async def _resolve_approver_agent(
        self,
        *,
        session: SessionRecord,
        source_job: JobRecord,
        explicit_approver_agent_id: str | None,
    ) -> str:
        if explicit_approver_agent_id is not None:
            return explicit_approver_agent_id
        if session.lead_agent_id is not None:
            return session.lead_agent_id
        return source_job.assigned_agent_id

    async def _record_session_event(
        self,
        *,
        session_id: str,
        event_type: str,
        actor_type: str | None,
        actor_id: str | None,
        payload: dict[str, object] | None,
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
