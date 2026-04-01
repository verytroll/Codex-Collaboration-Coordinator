"""Offline queue service for queued jobs."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.repositories.job_inputs import JobInputRecord, JobInputRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.services.relay_engine import RelayEngine, RelayExecutionResult
from app.services.rule_engine import RuleEngineService
from app.services.runtime_service import RuntimeService

DISPATCHABLE_RUNTIME_STATUSES = {"starting", "online", "busy"}
RETRYABLE_JOB_STATUSES = {"failed", "canceled", "paused_by_loop_guard"}
RESUMABLE_JOB_STATUSES = {"queued", "input_required", "auth_required", "paused_by_loop_guard"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class OfflineQueueDispatchResult:
    """Result of scheduling a job for dispatch or queueing."""

    job_id: str
    queued: bool
    relay_result: RelayExecutionResult | None


class OfflineQueueService:
    """Queue jobs while an agent runtime is offline and dispatch them later."""

    def __init__(
        self,
        *,
        job_repository: JobRepository,
        job_input_repository: JobInputRepository,
        runtime_service: RuntimeService,
        relay_engine: RelayEngine,
        rule_engine_service: RuleEngineService | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.job_input_repository = job_input_repository
        self.runtime_service = runtime_service
        self.relay_engine = relay_engine
        self.rule_engine_service = rule_engine_service

    async def schedule_job(
        self,
        job_id: str,
        *,
        input_type: str,
        input_payload: dict[str, Any] | None = None,
        relay_reason: str = "manual_relay",
    ) -> OfflineQueueDispatchResult:
        """Record a job input and dispatch immediately when the runtime is available."""
        job = await self._ensure_job(job_id)
        await self._record_input(
            job,
            input_type=input_type,
            input_payload=input_payload,
        )
        dispatch_allowed = True
        hold_reason: str | None = None
        if self.rule_engine_service is not None:
            dispatch_policy = await self.rule_engine_service.resolve_job_dispatch(job)
            dispatch_allowed = dispatch_policy.dispatch_allowed
            hold_reason = dispatch_policy.hold_reason
            if dispatch_policy.channel_key != job.channel_key:
                job = replace(job, channel_key=dispatch_policy.channel_key)
                await self.job_repository.update(job)
        if not dispatch_allowed:
            blocked_job = replace(
                job,
                status="input_required",
                last_known_turn_status=hold_reason or "rule_review_required",
                updated_at=_utc_now(),
            )
            await self.job_repository.update(blocked_job)
            return OfflineQueueDispatchResult(job_id=job.id, queued=True, relay_result=None)
        if not await self._is_dispatchable(job.assigned_agent_id):
            return OfflineQueueDispatchResult(job_id=job.id, queued=True, relay_result=None)
        relay_result = await self.relay_engine.execute_job(job.id, relay_reason=relay_reason)
        return OfflineQueueDispatchResult(job_id=job.id, queued=False, relay_result=relay_result)

    async def retry_job(
        self,
        job_id: str,
        *,
        reason: str | None = None,
    ) -> OfflineQueueDispatchResult:
        """Retry a terminal job and dispatch or queue it again."""
        job = await self._ensure_job(job_id)
        if job.status not in RETRYABLE_JOB_STATUSES:
            raise ValueError(f"Job {job.id} cannot be retried from status {job.status}")
        now = _utc_now()
        updated_job = replace(
            job,
            status="queued",
            last_known_turn_status="retry_requested",
            error_code=None,
            error_message=None,
            completed_at=None,
            updated_at=now,
        )
        await self.job_repository.update(updated_job)
        return await self.schedule_job(
            job.id,
            input_type="retry",
            input_payload={"reason": reason, "previous_status": job.status},
            relay_reason="manual_relay",
        )

    async def resume_job(
        self,
        job_id: str,
        *,
        reason: str | None = None,
    ) -> OfflineQueueDispatchResult:
        """Resume a paused or blocked job."""
        job = await self._ensure_job(job_id)
        if job.status not in RESUMABLE_JOB_STATUSES:
            raise ValueError(f"Job {job.id} cannot be resumed from status {job.status}")
        now = _utc_now()
        updated_job = replace(
            job,
            status="queued",
            last_known_turn_status="resumed",
            completed_at=None,
            updated_at=now,
        )
        await self.job_repository.update(updated_job)
        return await self.schedule_job(
            job.id,
            input_type="resume",
            input_payload={"reason": reason, "previous_status": job.status},
            relay_reason="manual_relay",
        )

    async def dispatch_pending_for_agent(self, agent_id: str) -> list[RelayExecutionResult]:
        """Dispatch all queued jobs for an agent if its runtime is currently online."""
        if not await self._is_dispatchable(agent_id):
            return []
        queued_jobs = [
            job
            for job in await self.job_repository.list_by_agent(agent_id)
            if job.status == "queued"
        ]
        results: list[RelayExecutionResult] = []
        for job in queued_jobs:
            try:
                results.append(
                    await self.relay_engine.execute_job(
                        job.id,
                        relay_reason="policy_auto_relay",
                    )
                )
            except Exception:
                continue
        return results

    async def _record_input(
        self,
        job: JobRecord,
        *,
        input_type: str,
        input_payload: dict[str, Any] | None,
    ) -> JobInputRecord:
        created_at = _utc_now()
        job_input = JobInputRecord(
            id=f"jni_{uuid4().hex}",
            job_id=job.id,
            session_id=job.session_id,
            input_type=input_type,
            input_payload_json=(
                json.dumps(input_payload, sort_keys=True) if input_payload is not None else None
            ),
            created_at=created_at,
        )
        return await self.job_input_repository.create(job_input)

    async def _ensure_job(self, job_id: str) -> JobRecord:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        return job

    async def _is_dispatchable(self, agent_id: str) -> bool:
        runtime = await self.runtime_service.get_latest_runtime_for_agent(agent_id)
        if runtime is None:
            return False
        return runtime.runtime_status in DISPATCHABLE_RUNTIME_STATUSES
