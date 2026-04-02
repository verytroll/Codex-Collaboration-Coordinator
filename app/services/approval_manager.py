"""Approval request management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.core.errors import ConflictError
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord, JobRepository
from app.repositories.session_events import SessionEventRepository
from app.services.session_events import record_session_event

APPROVAL_STATUSES = {"pending", "accepted", "declined", "canceled"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    """Result of changing an approval request."""

    approval: ApprovalRequestRecord
    job: JobRecord | None


class ApprovalManager:
    """Create and resolve approval requests."""

    def __init__(
        self,
        *,
        approval_repository: ApprovalRepository,
        job_repository: JobRepository,
        job_event_repository: JobEventRepository,
        session_event_repository: SessionEventRepository,
    ) -> None:
        self.approval_repository = approval_repository
        self.job_repository = job_repository
        self.job_event_repository = job_event_repository
        self.session_event_repository = session_event_repository

    async def create_request(
        self,
        *,
        job: JobRecord,
        approval_type: str,
        request_payload: dict[str, object],
        policy_metadata: dict[str, object] | None = None,
        requested_at: str | None = None,
    ) -> ApprovalRequestRecord:
        """Create a new approval request for a job."""
        created_at = requested_at or _utc_now()
        payload = dict(request_payload)
        if policy_metadata is not None:
            payload["policy_metadata"] = policy_metadata
        approval = ApprovalRequestRecord(
            id=f"apr_{uuid4().hex}",
            job_id=job.id,
            agent_id=job.assigned_agent_id,
            approval_type=approval_type,
            status="pending",
            request_payload_json=json.dumps(payload, sort_keys=True),
            decision_payload_json=None,
            requested_at=created_at,
            resolved_at=None,
            created_at=created_at,
            updated_at=created_at,
        )
        created = await self.approval_repository.create(approval)
        await self.job_event_repository.create(
            JobEventRecord(
                id=f"jbe_{uuid4().hex}",
                job_id=job.id,
                session_id=job.session_id,
                event_type="approval.required",
                event_payload_json=json.dumps(
                    {
                        "approval_id": created.id,
                        "approval_type": approval_type,
                        "policy_metadata": policy_metadata,
                    },
                    sort_keys=True,
                ),
                created_at=created_at,
            )
        )
        await record_session_event(
            self.session_event_repository,
            session_id=job.session_id,
            event_type="approval.required",
            actor_type="system",
            actor_id=None,
            payload={
                "job_id": job.id,
                "approval_id": created.id,
                "approval_type": approval_type,
                "policy_metadata": policy_metadata,
            },
            created_at=created_at,
        )
        return created

    async def accept(
        self,
        approval_id: str,
        *,
        decision_payload: dict[str, object] | None = None,
    ) -> ApprovalDecision:
        """Accept an approval request and reactivate its job."""
        return await self._resolve(
            approval_id,
            new_status="accepted",
            decision_payload=decision_payload,
        )

    async def decline(
        self,
        approval_id: str,
        *,
        decision_payload: dict[str, object] | None = None,
    ) -> ApprovalDecision:
        """Decline an approval request and cancel its job."""
        return await self._resolve(
            approval_id,
            new_status="declined",
            decision_payload=decision_payload,
        )

    async def _resolve(
        self,
        approval_id: str,
        *,
        new_status: str,
        decision_payload: dict[str, object] | None,
    ) -> ApprovalDecision:
        if new_status not in APPROVAL_STATUSES:
            raise ValueError(f"Unsupported approval status: {new_status}")

        approval = await self._get_approval(approval_id)
        if approval.status != "pending":
            raise ConflictError(f"Approval request already resolved: {approval_id}")

        now = _utc_now()
        updated_approval = ApprovalRequestRecord(
            id=approval.id,
            job_id=approval.job_id,
            agent_id=approval.agent_id,
            approval_type=approval.approval_type,
            status=new_status,
            request_payload_json=approval.request_payload_json,
            decision_payload_json=(
                json.dumps(decision_payload, sort_keys=True)
                if decision_payload is not None
                else None
            ),
            requested_at=approval.requested_at,
            resolved_at=now,
            created_at=approval.created_at,
            updated_at=now,
        )
        saved_approval = await self.approval_repository.update(updated_approval)
        job = await self._get_job(approval.job_id)
        updated_job = await self._update_job_for_decision(job, new_status, now)
        await self.job_event_repository.create(
            JobEventRecord(
                id=f"jbe_{uuid4().hex}",
                job_id=job.id,
                session_id=job.session_id,
                event_type=f"approval.{new_status}",
                event_payload_json=json.dumps(
                    {
                        "approval_id": approval.id,
                        "decision_payload": decision_payload,
                    },
                    sort_keys=True,
                ),
                created_at=now,
            )
        )
        await record_session_event(
            self.session_event_repository,
            session_id=job.session_id,
            event_type=f"approval.{new_status}",
            actor_type="system",
            actor_id=None,
            payload={
                "job_id": job.id,
                "approval_id": approval.id,
            },
            created_at=now,
        )
        return ApprovalDecision(approval=saved_approval, job=updated_job)

    async def _update_job_for_decision(
        self,
        job: JobRecord,
        new_status: str,
        now: str,
    ) -> JobRecord:
        if new_status == "accepted":
            updated = JobRecord(
                id=job.id,
                session_id=job.session_id,
                channel_key=job.channel_key,
                assigned_agent_id=job.assigned_agent_id,
                runtime_id=job.runtime_id,
                source_message_id=job.source_message_id,
                parent_job_id=job.parent_job_id,
                title=job.title,
                instructions=job.instructions,
                status="queued" if job.status == "input_required" else "running",
                hop_count=job.hop_count,
                priority=job.priority,
                codex_runtime_id=job.codex_runtime_id,
                codex_thread_id=job.codex_thread_id,
                active_turn_id=job.active_turn_id,
                last_known_turn_status="accepted",
                result_summary=job.result_summary,
                error_code=job.error_code,
                error_message=job.error_message,
                started_at=job.started_at or now,
                completed_at=job.completed_at,
                created_at=job.created_at,
                updated_at=now,
            )
        else:
            updated = JobRecord(
                id=job.id,
                session_id=job.session_id,
                channel_key=job.channel_key,
                assigned_agent_id=job.assigned_agent_id,
                runtime_id=job.runtime_id,
                source_message_id=job.source_message_id,
                parent_job_id=job.parent_job_id,
                title=job.title,
                instructions=job.instructions,
                status="canceled",
                hop_count=job.hop_count,
                priority=job.priority,
                codex_runtime_id=job.codex_runtime_id,
                codex_thread_id=job.codex_thread_id,
                active_turn_id=job.active_turn_id,
                last_known_turn_status="declined",
                result_summary=job.result_summary,
                error_code=job.error_code,
                error_message=job.error_message,
                started_at=job.started_at,
                completed_at=now,
                created_at=job.created_at,
                updated_at=now,
            )
        return await self.job_repository.update(updated)

    async def _get_approval(self, approval_id: str) -> ApprovalRequestRecord:
        approval = await self.approval_repository.get(approval_id)
        if approval is None:
            raise LookupError(f"Approval request not found: {approval_id}")
        return approval

    async def _get_job(self, job_id: str) -> JobRecord:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        return job
