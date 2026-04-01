"""Advanced policy engine and conditional automation."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.policies import (
    PolicyDecisionRecord,
    PolicyRecord,
    PolicyRepository,
)
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.phase_service import PhaseService
from app.services.session_events import record_session_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_json(payload: str | None) -> dict[str, Any]:
    if payload is None:
        return {}
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    """Resolved automation decision."""

    policy: PolicyRecord | None
    decision: str
    reason: str
    decision_record: PolicyDecisionRecord
    context: dict[str, Any]


class PolicyEngineV2Service:
    """Evaluate advanced policies and write decision audit records."""

    _ALLOWED_POLICY_TYPES = {
        "conditional_auto_approve",
        "escalation",
        "template_scoped",
        "phase_scoped",
    }

    def __init__(
        self,
        *,
        policy_repository: PolicyRepository,
        session_repository: SessionRepository,
        job_repository: JobRepository,
        phase_service: PhaseService,
        session_event_repository: SessionEventRepository,
    ) -> None:
        self.policy_repository = policy_repository
        self.session_repository = session_repository
        self.job_repository = job_repository
        self.phase_service = phase_service
        self.session_event_repository = session_event_repository

    async def list_policies(
        self,
        *,
        session_id: str | None = None,
        template_key: str | None = None,
        phase_key: str | None = None,
        active_only: bool = False,
    ) -> list[PolicyRecord]:
        """Return policies matching the requested scope."""
        return await self.policy_repository.list(
            session_id=session_id,
            template_key=template_key,
            phase_key=phase_key,
            active_only=active_only,
        )

    async def get_policy(self, policy_id: str) -> PolicyRecord | None:
        """Return a policy by id."""
        return await self.policy_repository.get(policy_id)

    async def list_decisions(
        self,
        *,
        policy_id: str | None = None,
        session_id: str | None = None,
    ) -> list[PolicyDecisionRecord]:
        """Return policy decision audits."""
        return await self.policy_repository.list_decisions(
            policy_id=policy_id,
            session_id=session_id,
        )

    async def create_policy(
        self,
        *,
        session_id: str | None,
        template_key: str | None,
        phase_key: str | None,
        policy_type: str,
        name: str,
        description: str | None = None,
        is_active: bool = True,
        automation_paused: bool = False,
        pause_reason: str | None = None,
        priority: int = 100,
        conditions: dict[str, Any] | None = None,
        actions: dict[str, Any] | None = None,
    ) -> PolicyRecord:
        """Create a new policy."""
        self._validate_policy_scope(session_id, template_key, phase_key)
        if policy_type not in self._ALLOWED_POLICY_TYPES:
            raise ValueError(f"Unsupported policy type: {policy_type}")
        now = _utc_now()
        policy = PolicyRecord(
            id=f"pol_{uuid4().hex}",
            session_id=session_id,
            template_key=template_key,
            phase_key=phase_key,
            policy_type=policy_type,
            name=name,
            description=description,
            is_active=1 if is_active else 0,
            automation_paused=1 if automation_paused else 0,
            pause_reason=pause_reason,
            priority=priority,
            conditions_json=json.dumps(conditions, sort_keys=True)
            if conditions is not None
            else None,
            actions_json=json.dumps(actions, sort_keys=True) if actions is not None else None,
            created_at=now,
            updated_at=now,
        )
        return await self.policy_repository.create(policy)

    async def activate_policy(self, policy_id: str) -> PolicyRecord:
        """Enable a policy for evaluation."""
        policy = await self._get_policy(policy_id)
        updated = replace(policy, is_active=1, updated_at=_utc_now())
        return await self.policy_repository.update(updated)

    async def deactivate_policy(self, policy_id: str) -> PolicyRecord:
        """Disable a policy."""
        policy = await self._get_policy(policy_id)
        updated = replace(policy, is_active=0, updated_at=_utc_now())
        return await self.policy_repository.update(updated)

    async def pause_automation(
        self,
        policy_id: str,
        *,
        reason: str | None = None,
    ) -> PolicyRecord:
        """Pause automation for a policy."""
        policy = await self._get_policy(policy_id)
        now = _utc_now()
        updated = replace(
            policy,
            automation_paused=1,
            pause_reason=reason,
            updated_at=now,
        )
        saved = await self.policy_repository.update(updated)
        await self._record_decision(
            policy=saved,
            session_id=saved.session_id,
            subject_type="policy_control",
            subject_id=saved.id,
            gate_type="automation_control",
            decision="paused",
            reason=reason or "automation paused",
            context={"reason": reason, "policy_id": saved.id},
        )
        return saved

    async def resume_automation(
        self,
        policy_id: str,
        *,
        reason: str | None = None,
    ) -> PolicyRecord:
        """Resume automation for a policy."""
        policy = await self._get_policy(policy_id)
        now = _utc_now()
        updated = replace(
            policy,
            automation_paused=0,
            pause_reason=None,
            updated_at=now,
        )
        saved = await self.policy_repository.update(updated)
        await self._record_decision(
            policy=saved,
            session_id=saved.session_id,
            subject_type="policy_control",
            subject_id=saved.id,
            gate_type="automation_control",
            decision="resumed",
            reason=reason or "automation resumed",
            context={"reason": reason, "policy_id": saved.id},
        )
        return saved

    async def evaluate_approval_gate(
        self,
        *,
        session_id: str,
        source_job_id: str,
        success_phase_key: str,
        failure_phase_key: str,
        approval_type: str,
        requested_by_agent_id: str | None = None,
        approver_agent_id: str | None = None,
        notes: str | None = None,
    ) -> PolicyEvaluationResult:
        """Resolve policy for an approval gate request."""
        session = await self._get_session(session_id)
        source_job = await self._get_job(source_job_id)
        current_phase = await self.phase_service.get_active_phase(session_id)
        context = {
            "session_id": session.id,
            "template_key": session.template_key,
            "current_phase_key": current_phase.phase_key if current_phase is not None else None,
            "phase_key": success_phase_key,
            "failure_phase_key": failure_phase_key,
            "gate_type": "approval_required",
            "approval_type": approval_type,
            "source_job_id": source_job.id,
            "job_status": source_job.status,
            "assigned_agent_id": source_job.assigned_agent_id,
            "requested_by_agent_id": requested_by_agent_id,
            "approver_agent_id": approver_agent_id,
            "channel_key": source_job.channel_key,
            "priority": source_job.priority,
            "notes": notes,
        }
        return await self._evaluate(
            subject_type="approval_gate",
            subject_id=source_job.id,
            gate_type="approval_required",
            session=session,
            context=context,
        )

    async def evaluate_review_gate(
        self,
        *,
        session_id: str,
        source_job_id: str,
        phase_key: str,
        reviewer_agent_id: str | None = None,
        requested_by_agent_id: str | None = None,
        notes: str | None = None,
    ) -> PolicyEvaluationResult:
        """Resolve policy for a review gate request."""
        session = await self._get_session(session_id)
        source_job = await self._get_job(source_job_id)
        current_phase = await self.phase_service.get_active_phase(session_id)
        context = {
            "session_id": session.id,
            "template_key": session.template_key,
            "current_phase_key": current_phase.phase_key if current_phase is not None else None,
            "phase_key": phase_key,
            "gate_type": "review_required",
            "source_job_id": source_job.id,
            "job_status": source_job.status,
            "assigned_agent_id": source_job.assigned_agent_id,
            "requested_by_agent_id": requested_by_agent_id,
            "reviewer_agent_id": reviewer_agent_id,
            "channel_key": source_job.channel_key,
            "priority": source_job.priority,
            "notes": notes,
        }
        return await self._evaluate(
            subject_type="review_gate",
            subject_id=source_job.id,
            gate_type="review_required",
            session=session,
            context=context,
        )

    async def _evaluate(
        self,
        *,
        subject_type: str,
        subject_id: str,
        gate_type: str,
        session: SessionRecord,
        context: dict[str, Any],
    ) -> PolicyEvaluationResult:
        candidates = await self.policy_repository.list(
            session_id=session.id,
            template_key=session.template_key,
            phase_key=context.get("phase_key")
            if isinstance(context.get("phase_key"), str)
            else None,
            active_only=False,
        )
        for policy in candidates:
            if not policy.is_active:
                continue
            if policy.automation_paused:
                if not self._matches_policy(policy, context=context):
                    continue
                reason = (
                    f"Policy {policy.name} is paused and gate handling fell back to manual"
                )
                record = await self._record_decision(
                    policy=policy,
                    session_id=session.id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    gate_type=gate_type,
                    decision="allow",
                    reason=reason,
                    context=context,
                )
                return PolicyEvaluationResult(
                    policy=policy,
                    decision="allow",
                    reason=reason,
                    decision_record=record,
                    context=context,
                )
            if not self._matches_policy(policy, context=context):
                continue
            decision = self._resolve_decision(policy)
            reason = self._resolve_reason(policy, decision)
            record = await self._record_decision(
                policy=policy,
                session_id=session.id,
                subject_type=subject_type,
                subject_id=subject_id,
                gate_type=gate_type,
                decision=decision,
                reason=reason,
                context=context,
            )
            return PolicyEvaluationResult(
                policy=policy,
                decision=decision,
                reason=reason,
                decision_record=record,
                context=context,
            )

        record = await self._record_decision(
            policy=None,
            session_id=session.id,
            subject_type=subject_type,
            subject_id=subject_id,
            gate_type=gate_type,
            decision="allow",
            reason="no_matching_policy",
            context=context,
        )
        return PolicyEvaluationResult(
            policy=None,
            decision="allow",
            reason="no_matching_policy",
            decision_record=record,
            context=context,
        )

    async def _record_decision(
        self,
        *,
        policy: PolicyRecord | None,
        session_id: str | None,
        subject_type: str,
        subject_id: str,
        gate_type: str,
        decision: str,
        reason: str,
        context: dict[str, Any],
    ) -> PolicyDecisionRecord:
        now = _utc_now()
        record = PolicyDecisionRecord(
            id=f"pdc_{uuid4().hex}",
            policy_id=policy.id if policy is not None else None,
            session_id=session_id,
            subject_type=subject_type,
            subject_id=subject_id,
            gate_type=gate_type,
            decision=decision,
            matched=1 if policy is not None else 0,
            reason=reason,
            context_json=json.dumps(context, sort_keys=True),
            created_at=now,
        )
        saved = await self.policy_repository.create_decision(record)
        if session_id is not None:
            await record_session_event(
                self.session_event_repository,
                session_id=session_id,
                event_type="policy.decision.recorded",
                actor_type="system",
                actor_id=None,
                payload={
                    "policy_id": saved.policy_id,
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "gate_type": gate_type,
                    "decision": decision,
                    "reason": reason,
                },
                created_at=now,
            )
        return saved

    def _matches_policy(self, policy: PolicyRecord, *, context: dict[str, Any]) -> bool:
        conditions = _parse_json(policy.conditions_json)
        for key, expected in conditions.items():
            if not self._matches_expected(expected, context.get(key)):
                return False
        return True

    def _matches_expected(self, expected: Any, actual: Any) -> bool:
        if isinstance(expected, dict):
            if "equals" in expected:
                return actual == expected["equals"]
            if "any_of" in expected and isinstance(expected["any_of"], list):
                return actual in expected["any_of"]
            if "contains" in expected and isinstance(actual, str):
                needle = expected["contains"]
                return isinstance(needle, str) and needle.lower() in actual.lower()
            if "not" in expected:
                return not self._matches_expected(expected["not"], actual)
        if isinstance(expected, list):
            return actual in expected
        return actual == expected

    def _resolve_decision(self, policy: PolicyRecord) -> str:
        actions = _parse_json(policy.actions_json)
        decision = actions.get("decision")
        if isinstance(decision, str) and decision in {
            "allow",
            "auto_approve",
            "escalate_review",
            "paused",
            "resumed",
            "deferred",
        }:
            return decision
        if policy.policy_type == "conditional_auto_approve":
            return "auto_approve"
        if policy.policy_type == "escalation":
            return "escalate_review"
        return "allow"

    def _resolve_reason(self, policy: PolicyRecord, decision: str) -> str:
        actions = _parse_json(policy.actions_json)
        reason = actions.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
        if decision == "auto_approve":
            return f"Policy {policy.name} auto-approved the gate"
        if decision == "escalate_review":
            return f"Policy {policy.name} escalated the gate to review"
        if decision == "paused":
            return f"Policy {policy.name} paused automation"
        if decision == "resumed":
            return f"Policy {policy.name} resumed automation"
        return f"Policy {policy.name} allowed the gate"

    async def _get_policy(self, policy_id: str) -> PolicyRecord:
        policy = await self.policy_repository.get(policy_id)
        if policy is None:
            raise LookupError(f"Policy not found: {policy_id}")
        return policy

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

    @staticmethod
    def _validate_policy_scope(
        session_id: str | None,
        template_key: str | None,
        phase_key: str | None,
    ) -> None:
        if session_id is None and template_key is None and phase_key is None:
            raise ValueError("Policy scope requires session_id, template_key, or phase_key")
