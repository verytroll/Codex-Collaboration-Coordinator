"""Operator dashboard aggregation service."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.core.telemetry import get_telemetry_service
from app.repositories.a2a_tasks import A2ATaskRepository
from app.repositories.approvals import ApprovalRepository
from app.repositories.jobs import JobRepository
from app.repositories.orchestration_runs import OrchestrationRunRepository
from app.repositories.outbound_webhooks import (
    OutboundWebhookDeliveryRepository,
    OutboundWebhookRegistrationRepository,
)
from app.repositories.phases import PhaseRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.runtime_pools import WorkContextRepository
from app.repositories.sessions import SessionRepository
from app.services.debug_service import DebugService
from app.services.runtime_pool_service import RuntimePoolService

logger = get_logger(__name__)

BLOCKED_JOB_STATUSES = {"input_required", "auth_required", "paused_by_loop_guard"}
PENDING_REVIEW_STATUS = "requested"
PENDING_GATE_STATUS = "pending"
PENDING_APPROVAL_STATUS = "pending"
PENDING_TASK_STATUSES = {"queued", "running", "input_required", "auth_required"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class OperatorDashboardFilters:
    """Standard filters shared by operator dashboard surfaces."""

    session_id: str | None = None
    template_key: str | None = None
    phase_key: str | None = None
    runtime_pool_key: str | None = None


@dataclass(frozen=True, slots=True)
class OperatorDashboardSnapshot:
    """Loaded operator state and lookup indexes."""

    sessions: list[Any]
    phases: list[Any]
    jobs: list[Any]
    reviews: list[Any]
    runs: list[Any]
    contexts: list[Any]
    tasks: list[Any]
    approvals: list[Any]
    outbound_registrations: list[Any]
    outbound_deliveries: list[Any]
    pool_diagnostics: dict[str, Any]
    session_by_id: dict[str, Any]
    phase_key_by_session_id: dict[str, str | None]
    job_by_id: dict[str, Any]
    job_pool_key_by_id: dict[str, str | None]
    job_phase_key_by_id: dict[str, str | None]
    context_pool_key_by_job_id: dict[str, str | None]
    task_pool_key_by_id: dict[str, str | None]
    task_phase_key_by_id: dict[str, str | None]


class OperatorDashboardService:
    """Build operator dashboard and debug aggregates from repositories."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        phase_repository: PhaseRepository,
        job_repository: JobRepository,
        review_repository: ReviewRepository,
        orchestration_run_repository: OrchestrationRunRepository,
        runtime_pool_service: RuntimePoolService,
        work_context_repository: WorkContextRepository,
        a2a_task_repository: A2ATaskRepository,
        approval_repository: ApprovalRepository,
        outbound_webhook_registration_repository: OutboundWebhookRegistrationRepository,
        outbound_webhook_delivery_repository: OutboundWebhookDeliveryRepository,
        debug_service: DebugService,
    ) -> None:
        self.session_repository = session_repository
        self.phase_repository = phase_repository
        self.job_repository = job_repository
        self.review_repository = review_repository
        self.orchestration_run_repository = orchestration_run_repository
        self.runtime_pool_service = runtime_pool_service
        self.work_context_repository = work_context_repository
        self.a2a_task_repository = a2a_task_repository
        self.approval_repository = approval_repository
        self.outbound_webhook_registration_repository = outbound_webhook_registration_repository
        self.outbound_webhook_delivery_repository = outbound_webhook_delivery_repository
        self.debug_service = debug_service

    async def get_dashboard(
        self,
        filters: OperatorDashboardFilters | None = None,
    ) -> dict[str, Any]:
        """Return dashboard aggregates for operators."""
        snapshot = await self._load_snapshot()
        resolved_filters = filters or OperatorDashboardFilters()
        filtered = self._filter_snapshot(snapshot, resolved_filters)
        payload = self._build_dashboard(filtered, resolved_filters)
        await get_telemetry_service().record_sample(
            "operator_dashboard",
            metrics=self._telemetry_metrics(
                snapshot=filtered,
                dashboard=payload,
            ),
        )
        payload["telemetry"] = await get_telemetry_service().get_surface()
        logger.info("operator dashboard generated")
        return payload

    async def get_debug_surface(
        self,
        filters: OperatorDashboardFilters | None = None,
    ) -> dict[str, Any]:
        """Return the dashboard plus the legacy compact debug surface."""
        dashboard = await self.get_dashboard(filters)
        return {
            "dashboard": dashboard,
            "debug": await self.debug_service.get_surface(),
        }

    async def _load_snapshot(self) -> OperatorDashboardSnapshot:
        (
            sessions,
            phases,
            jobs,
            reviews,
            runs,
            contexts,
            tasks,
            approvals,
            outbound_registrations,
            outbound_deliveries,
            pool_diagnostics,
        ) = await asyncio.gather(
            self.session_repository.list(),
            self.phase_repository.list(),
            self.job_repository.list(),
            self.review_repository.list(),
            self.orchestration_run_repository.list(),
            self.work_context_repository.list(),
            self.a2a_task_repository.list(),
            self.approval_repository.list(),
            self.outbound_webhook_registration_repository.list(),
            self.outbound_webhook_delivery_repository.list(),
            self.runtime_pool_service.get_pool_diagnostics(),
        )
        session_by_id = {session.id: session for session in sessions}
        phase_by_id = {phase.id: phase for phase in phases}
        phase_key_by_session_id = {
            session.id: (
                phase_by_id[session.active_phase_id].phase_key
                if session.active_phase_id is not None and session.active_phase_id in phase_by_id
                else None
            )
            for session in sessions
        }
        job_by_id = {job.id: job for job in jobs}
        pool_key_by_id = self._pool_key_by_id(pool_diagnostics)
        context_pool_key_by_job_id = {
            context.job_id: pool_key_by_id.get(context.runtime_pool_id) for context in contexts
        }
        job_pool_key_by_id = {
            job_id: context_pool_key_by_job_id.get(job_id) for job_id in job_by_id
        }
        job_phase_key_by_id = {job.id: phase_key_by_session_id.get(job.session_id) for job in jobs}
        task_pool_key_by_id = {task.id: job_pool_key_by_id.get(task.job_id) for task in tasks}
        task_phase_key_by_id = {task.id: job_phase_key_by_id.get(task.job_id) for task in tasks}
        return OperatorDashboardSnapshot(
            sessions=sessions,
            phases=phases,
            jobs=jobs,
            reviews=reviews,
            runs=runs,
            contexts=contexts,
            tasks=tasks,
            approvals=approvals,
            outbound_registrations=outbound_registrations,
            outbound_deliveries=outbound_deliveries,
            pool_diagnostics=pool_diagnostics,
            session_by_id=session_by_id,
            phase_key_by_session_id=phase_key_by_session_id,
            job_by_id=job_by_id,
            job_pool_key_by_id=job_pool_key_by_id,
            job_phase_key_by_id=job_phase_key_by_id,
            context_pool_key_by_job_id=context_pool_key_by_job_id,
            task_pool_key_by_id=task_pool_key_by_id,
            task_phase_key_by_id=task_phase_key_by_id,
        )

    def _build_dashboard(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> dict[str, Any]:
        queue_heat = self._build_queue_heat(snapshot, filters)
        phase_distribution = self._build_phase_distribution(snapshot, filters)
        review_bottlenecks = self._build_review_bottlenecks(snapshot, filters)
        runtime_pools = self._build_runtime_pool_health(snapshot, filters)
        public_task_throughput = self._build_public_task_throughput(snapshot, filters)
        outbound_webhooks = self._build_outbound_webhook_summary(snapshot, filters)
        bottlenecks = self._build_bottlenecks(
            phase_distribution=phase_distribution,
            review_bottlenecks=review_bottlenecks,
            runtime_pools=runtime_pools,
        )
        diagnostics = self._build_diagnostics(
            bottlenecks=bottlenecks,
            runtime_pools=runtime_pools,
            public_task_throughput=public_task_throughput,
            outbound_webhooks=outbound_webhooks,
        )
        return {
            "generated_at": _utc_now(),
            "filters": {
                "session_id": filters.session_id,
                "template_key": filters.template_key,
                "phase_key": filters.phase_key,
                "runtime_pool_key": filters.runtime_pool_key,
            },
            "bottlenecks": bottlenecks,
            "queue_heat": queue_heat,
            "phase_distribution": phase_distribution,
            "review_bottlenecks": review_bottlenecks,
            "runtime_pools": runtime_pools,
            "public_task_throughput": public_task_throughput,
            "outbound_webhooks": outbound_webhooks,
            "diagnostics": diagnostics,
        }

    def _build_queue_heat(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str | None, str | None], dict[str, Any]] = defaultdict(
            lambda: {"queued_jobs": 0, "running_jobs": 0, "blocked_jobs": 0, "total_jobs": 0}
        )
        for job in snapshot.jobs:
            session = snapshot.session_by_id.get(job.session_id)
            if session is None or not self._job_matches(job, session, snapshot, filters):
                continue
            phase_key = snapshot.job_phase_key_by_id.get(job.id)
            pool_key = snapshot.job_pool_key_by_id.get(job.id)
            item = groups[(job.session_id, phase_key, pool_key)]
            item["session_id"] = job.session_id
            item["session_title"] = session.title
            item["phase_key"] = phase_key
            item["runtime_pool_key"] = pool_key
            item["total_jobs"] += 1
            if job.status == "queued":
                item["queued_jobs"] += 1
            elif job.status == "running":
                item["running_jobs"] += 1
            elif job.status in BLOCKED_JOB_STATUSES:
                item["blocked_jobs"] += 1
        items = list(groups.values())
        items.sort(
            key=lambda item: (
                -(item["queued_jobs"] + item["running_jobs"] + item["blocked_jobs"]),
                item["session_id"],
                item["phase_key"] or "",
                item["runtime_pool_key"] or "",
            )
        )
        return items

    def _build_phase_distribution(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> list[dict[str, Any]]:
        groups: dict[str, Counter[str]] = defaultdict(Counter)
        for session in snapshot.sessions:
            phase_key = snapshot.phase_key_by_session_id.get(session.id)
            if phase_key is None or not self._session_matches(
                session,
                phase_key,
                snapshot,
                filters,
            ):
                continue
            groups[phase_key]["session_count"] += 1
        for job in snapshot.jobs:
            session = snapshot.session_by_id.get(job.session_id)
            phase_key = snapshot.job_phase_key_by_id.get(job.id)
            if session is None or phase_key is None:
                continue
            if not self._job_matches(job, session, snapshot, filters):
                continue
            if job.status == "queued":
                groups[phase_key]["queued_jobs"] += 1
            elif job.status == "running":
                groups[phase_key]["running_jobs"] += 1
            elif job.status in BLOCKED_JOB_STATUSES:
                groups[phase_key]["blocked_jobs"] += 1
        for review in snapshot.reviews:
            session = snapshot.session_by_id.get(review.session_id)
            phase_key = snapshot.phase_key_by_session_id.get(review.session_id)
            if session is None or phase_key is None:
                continue
            if not self._review_matches(review, session, snapshot, filters):
                continue
            if review.review_status == PENDING_REVIEW_STATUS:
                groups[phase_key]["pending_reviews"] += 1
        for run in snapshot.runs:
            session = snapshot.session_by_id.get(run.session_id)
            if session is None or not self._run_matches(run, session, snapshot, filters):
                continue
            phase_key = run.current_phase_key or run.pending_phase_key or run.failure_phase_key
            if phase_key is not None and run.gate_status == PENDING_GATE_STATUS:
                groups[phase_key]["pending_gates"] += 1
        for task in snapshot.tasks:
            phase_key = snapshot.task_phase_key_by_id.get(task.id)
            if phase_key is None or not self._task_matches(task, snapshot, filters):
                continue
            groups[phase_key]["task_count"] += 1
        items = [
            {
                "phase_key": phase_key,
                "session_count": counts.get("session_count", 0),
                "queued_jobs": counts.get("queued_jobs", 0),
                "running_jobs": counts.get("running_jobs", 0),
                "blocked_jobs": counts.get("blocked_jobs", 0),
                "pending_reviews": counts.get("pending_reviews", 0),
                "pending_gates": counts.get("pending_gates", 0),
                "task_count": counts.get("task_count", 0),
            }
            for phase_key, counts in groups.items()
        ]
        items.sort(
            key=lambda item: (
                -(
                    item["blocked_jobs"]
                    + item["pending_reviews"]
                    + item["pending_gates"]
                    + item["queued_jobs"]
                    + item["running_jobs"]
                    + item["task_count"]
                ),
                item["phase_key"],
            )
        )
        return items

    def _build_review_bottlenecks(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(
            lambda: {"pending_reviews": 0, "oldest_requested_at": None, "newest_requested_at": None}
        )
        for review in snapshot.reviews:
            session = snapshot.session_by_id.get(review.session_id)
            if session is None or review.review_status != PENDING_REVIEW_STATUS:
                continue
            if not self._review_matches(review, session, snapshot, filters):
                continue
            item = groups[
                (
                    review.session_id,
                    review.template_key,
                    review.review_channel_key,
                    review.review_scope,
                )
            ]
            item["session_id"] = review.session_id
            item["session_title"] = session.title
            item["template_key"] = review.template_key
            item["review_channel_key"] = review.review_channel_key
            item["review_scope"] = review.review_scope
            item["pending_reviews"] += 1
            item["oldest_requested_at"] = self._earliest(
                item["oldest_requested_at"],
                review.requested_at,
            )
            item["newest_requested_at"] = self._latest(
                item["newest_requested_at"],
                review.requested_at,
            )
        items = list(groups.values())
        items.sort(
            key=lambda item: (
                -item["pending_reviews"],
                item["session_id"],
                item["template_key"],
                item["review_channel_key"],
            )
        )
        return items

    def _build_runtime_pool_health(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> list[dict[str, Any]]:
        pool_map = self._pool_map(snapshot.pool_diagnostics)
        counts_by_pool: dict[str, Counter[str]] = defaultdict(Counter)
        for job in snapshot.jobs:
            session = snapshot.session_by_id.get(job.session_id)
            if session is None or not self._job_matches(job, session, snapshot, filters):
                continue
            pool_key = snapshot.job_pool_key_by_id.get(job.id)
            if pool_key is not None:
                counts_by_pool[pool_key][job.status] += 1
        for review in snapshot.reviews:
            session = snapshot.session_by_id.get(review.session_id)
            if session is None or not self._review_matches(review, session, snapshot, filters):
                continue
            pool_key = snapshot.job_pool_key_by_id.get(review.source_job_id or "")
            if pool_key is not None and review.review_status == PENDING_REVIEW_STATUS:
                counts_by_pool[pool_key]["pending_reviews"] += 1
        for task in snapshot.tasks:
            if not self._task_matches(task, snapshot, filters):
                continue
            pool_key = snapshot.task_pool_key_by_id.get(task.id)
            if pool_key is not None and task.task_status in PENDING_TASK_STATUSES:
                counts_by_pool[pool_key]["pending_tasks"] += 1
        items = []
        for pool in pool_map.values():
            pool_key = pool["pool_key"]
            if filters.runtime_pool_key is not None and pool_key != filters.runtime_pool_key:
                continue
            group = counts_by_pool.get(pool_key, Counter())
            items.append(
                {
                    "id": pool["id"],
                    "pool_key": pool_key,
                    "title": pool["title"],
                    "pool_status": pool["pool_status"],
                    "max_active_contexts": pool["max_active_contexts"],
                    "active_context_count": pool["active_context_count"],
                    "waiting_context_count": pool["waiting_context_count"],
                    "borrowed_context_count": pool["borrowed_context_count"],
                    "available_runtime_count": pool["available_runtime_count"],
                    "utilization_ratio": pool["utilization_ratio"],
                    "queued_jobs": int(group.get("queued", 0)),
                    "blocked_jobs": int(
                        group.get("input_required", 0)
                        + group.get("auth_required", 0)
                        + group.get("paused_by_loop_guard", 0)
                    ),
                    "pending_reviews": int(group.get("pending_reviews", 0)),
                    "pending_tasks": int(group.get("pending_tasks", 0)),
                    "created_at": pool["created_at"],
                    "updated_at": pool["updated_at"],
                }
            )
        items.sort(
            key=lambda item: (
                -(
                    item["blocked_jobs"]
                    + item["queued_jobs"]
                    + item["waiting_context_count"]
                    + item["pending_reviews"]
                    + item["pending_tasks"]
                ),
                item["pool_key"],
            )
        )
        return items

    def _build_public_task_throughput(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> dict[str, Any]:
        counts = Counter()
        for task in snapshot.tasks:
            if self._task_matches(task, snapshot, filters):
                counts[task.task_status] += 1
        return {
            "total_tasks": sum(counts.values()),
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "input_required": counts.get("input_required", 0),
            "auth_required": counts.get("auth_required", 0),
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "canceled": counts.get("canceled", 0),
        }

    def _build_outbound_webhook_summary(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> dict[str, Any]:
        registrations = [
            item
            for item in snapshot.outbound_registrations
            if self._outbound_registration_matches(item, snapshot, filters)
        ]
        registration_ids = {item.id for item in registrations}
        deliveries = [
            item
            for item in snapshot.outbound_deliveries
            if item.registration_id in registration_ids
            and self._outbound_delivery_matches(item, snapshot, filters)
        ]
        return {
            "registrations": len(registrations),
            "active_registrations": sum(1 for item in registrations if item.status == "active"),
            "disabled_registrations": sum(1 for item in registrations if item.status != "active"),
            "pending_deliveries": sum(1 for item in deliveries if item.status == "pending"),
            "retrying_deliveries": sum(1 for item in deliveries if item.status == "retrying"),
            "failed_deliveries": sum(1 for item in deliveries if item.status == "failed"),
            "delivered_deliveries": sum(1 for item in deliveries if item.status == "delivered"),
        }

    def _build_bottlenecks(
        self,
        *,
        phase_distribution: list[dict[str, Any]],
        review_bottlenecks: list[dict[str, Any]],
        runtime_pools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        bottlenecks: list[dict[str, Any]] = []
        for phase in phase_distribution:
            count = phase["blocked_jobs"] + phase["pending_reviews"] + phase["pending_gates"]
            if count > 0:
                bottlenecks.append(
                    {
                        "kind": "phase",
                        "key": phase["phase_key"],
                        "count": count,
                        "detail": (
                            f"{phase['blocked_jobs']} blocked jobs, "
                            f"{phase['pending_reviews']} pending reviews, "
                            f"{phase['pending_gates']} pending gates"
                        ),
                    }
                )
        for pool in runtime_pools:
            count = (
                pool["blocked_jobs"]
                + pool["queued_jobs"]
                + pool["waiting_context_count"]
                + pool["pending_reviews"]
                + pool["pending_tasks"]
            )
            if count > 0:
                bottlenecks.append(
                    {
                        "kind": "runtime_pool",
                        "key": pool["pool_key"],
                        "count": count,
                        "detail": (
                            f"{pool['blocked_jobs']} blocked jobs, "
                            f"{pool['waiting_context_count']} waiting contexts, "
                            f"{pool['pending_reviews']} pending reviews"
                        ),
                    }
                )
        for review in review_bottlenecks:
            bottlenecks.append(
                {
                    "kind": "review",
                    "key": (
                        f"{review['session_id']}:{review['template_key']}:"
                        f"{review['review_channel_key']}"
                    ),
                    "count": review["pending_reviews"],
                    "detail": review["review_scope"],
                }
            )
        bottlenecks.sort(key=lambda item: (-item["count"], item["kind"], item["key"]))
        return bottlenecks[:10]

    def _build_diagnostics(
        self,
        *,
        bottlenecks: list[dict[str, Any]],
        runtime_pools: list[dict[str, Any]],
        public_task_throughput: dict[str, Any],
        outbound_webhooks: dict[str, Any],
    ) -> list[str]:
        diagnostics: list[str] = []
        if bottlenecks:
            top = bottlenecks[0]
            diagnostics.append(
                f"Top bottleneck: {top['kind']} {top['key']} ({top['count']} signal(s))."
            )
        else:
            diagnostics.append("No active bottlenecks detected.")
        degraded_pools = [
            pool["pool_key"] for pool in runtime_pools if pool["pool_status"] != "ready"
        ]
        if degraded_pools:
            diagnostics.append(
                f"{len(degraded_pools)} runtime pool(s) are not ready: {', '.join(degraded_pools)}."
            )
        active_tasks = (
            public_task_throughput["queued"]
            + public_task_throughput["running"]
            + public_task_throughput["input_required"]
            + public_task_throughput["auth_required"]
        )
        if active_tasks > 0:
            diagnostics.append(f"{active_tasks} public task(s) are still in flight.")
        if (
            outbound_webhooks["failed_deliveries"] > 0
            or outbound_webhooks["retrying_deliveries"] > 0
        ):
            diagnostics.append("Outbound webhooks have pending retries or failures.")
        return diagnostics

    def _filter_snapshot(
        self,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> OperatorDashboardSnapshot:
        sessions = [
            session
            for session in snapshot.sessions
            if self._session_matches(
                session,
                snapshot.phase_key_by_session_id.get(session.id),
                snapshot,
                filters,
            )
        ]
        jobs = [
            job
            for job in snapshot.jobs
            if self._job_matches(job, snapshot.session_by_id.get(job.session_id), snapshot, filters)
        ]
        reviews = [
            review
            for review in snapshot.reviews
            if self._review_matches(
                review,
                snapshot.session_by_id.get(review.session_id),
                snapshot,
                filters,
            )
        ]
        runs = [
            run
            for run in snapshot.runs
            if self._run_matches(run, snapshot.session_by_id.get(run.session_id), snapshot, filters)
        ]
        contexts = [
            context
            for context in snapshot.contexts
            if self._context_matches(context, snapshot, filters)
        ]
        tasks = [task for task in snapshot.tasks if self._task_matches(task, snapshot, filters)]
        approvals = [
            approval
            for approval in snapshot.approvals
            if self._approval_matches(approval, snapshot, filters)
        ]
        outbound_registrations = [
            item
            for item in snapshot.outbound_registrations
            if self._outbound_registration_matches(item, snapshot, filters)
        ]
        registration_ids = {item.id for item in outbound_registrations}
        outbound_deliveries = [
            item
            for item in snapshot.outbound_deliveries
            if item.registration_id in registration_ids
            and self._outbound_delivery_matches(item, snapshot, filters)
        ]
        return OperatorDashboardSnapshot(
            sessions=sessions,
            phases=snapshot.phases,
            jobs=jobs,
            reviews=reviews,
            runs=runs,
            contexts=contexts,
            tasks=tasks,
            approvals=approvals,
            outbound_registrations=outbound_registrations,
            outbound_deliveries=outbound_deliveries,
            pool_diagnostics=self._filter_pool_diagnostics(snapshot.pool_diagnostics, filters),
            session_by_id=snapshot.session_by_id,
            phase_key_by_session_id=snapshot.phase_key_by_session_id,
            job_by_id=snapshot.job_by_id,
            job_pool_key_by_id=snapshot.job_pool_key_by_id,
            job_phase_key_by_id=snapshot.job_phase_key_by_id,
            context_pool_key_by_job_id=snapshot.context_pool_key_by_job_id,
            task_pool_key_by_id=snapshot.task_pool_key_by_id,
            task_phase_key_by_id=snapshot.task_phase_key_by_id,
        )

    def _session_matches(
        self,
        session: Any,
        phase_key: str | None,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if filters.session_id is not None and session.id != filters.session_id:
            return False
        if filters.phase_key is not None and phase_key != filters.phase_key:
            return False
        if filters.runtime_pool_key is not None:
            return any(
                snapshot.job_pool_key_by_id.get(job.id) == filters.runtime_pool_key
                for job in snapshot.jobs
                if job.session_id == session.id
            )
        return True

    def _job_matches(
        self,
        job: Any,
        session: Any | None,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if session is None:
            return False
        if filters.session_id is not None and job.session_id != filters.session_id:
            return False
        if (
            filters.phase_key is not None
            and snapshot.job_phase_key_by_id.get(job.id) != filters.phase_key
        ):
            return False
        if (
            filters.runtime_pool_key is not None
            and snapshot.job_pool_key_by_id.get(job.id) != filters.runtime_pool_key
        ):
            return False
        return True

    def _review_matches(
        self,
        review: Any,
        session: Any | None,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if session is None or review.review_status != PENDING_REVIEW_STATUS:
            return False
        if filters.session_id is not None and review.session_id != filters.session_id:
            return False
        if (
            filters.phase_key is not None
            and snapshot.phase_key_by_session_id.get(review.session_id) != filters.phase_key
        ):
            return False
        if filters.template_key is not None and review.template_key != filters.template_key:
            return False
        if (
            filters.runtime_pool_key is not None
            and self._job_pool_key_for_job_id(snapshot, review.source_job_id)
            != filters.runtime_pool_key
        ):
            return False
        return True

    def _run_matches(
        self,
        run: Any,
        session: Any | None,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if session is None:
            return False
        if filters.session_id is not None and run.session_id != filters.session_id:
            return False
        phase_key = run.current_phase_key or run.pending_phase_key or run.failure_phase_key
        if filters.phase_key is not None and phase_key != filters.phase_key:
            return False
        if (
            filters.runtime_pool_key is not None
            and self._job_pool_key_for_job_id(snapshot, run.source_job_id)
            != filters.runtime_pool_key
        ):
            return False
        return True

    def _context_matches(
        self,
        context: Any,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if filters.session_id is not None and context.session_id != filters.session_id:
            return False
        if (
            filters.runtime_pool_key is not None
            and snapshot.context_pool_key_by_job_id.get(context.job_id) != filters.runtime_pool_key
        ):
            return False
        if (
            filters.phase_key is not None
            and snapshot.job_phase_key_by_id.get(context.job_id) != filters.phase_key
        ):
            return False
        return True

    def _task_matches(
        self,
        task: Any,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if filters.session_id is not None and task.session_id != filters.session_id:
            return False
        if (
            filters.phase_key is not None
            and snapshot.task_phase_key_by_id.get(task.id) != filters.phase_key
        ):
            return False
        if (
            filters.runtime_pool_key is not None
            and snapshot.task_pool_key_by_id.get(task.id) != filters.runtime_pool_key
        ):
            return False
        if filters.template_key is not None and task.relay_template_key != filters.template_key:
            return False
        return True

    def _approval_matches(
        self,
        approval: Any,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if approval.status != PENDING_APPROVAL_STATUS:
            return False
        job = snapshot.job_by_id.get(approval.job_id)
        if job is None:
            return False
        if filters.session_id is not None and job.session_id != filters.session_id:
            return False
        if (
            filters.phase_key is not None
            and snapshot.job_phase_key_by_id.get(job.id) != filters.phase_key
        ):
            return False
        if (
            filters.runtime_pool_key is not None
            and snapshot.job_pool_key_by_id.get(job.id) != filters.runtime_pool_key
        ):
            return False
        return True

    def _outbound_registration_matches(
        self,
        registration: Any,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if filters.session_id is not None and registration.session_id != filters.session_id:
            return False
        task = self._task_by_public_task_id(snapshot, registration.task_id)
        if task is None:
            return filters.session_id is None
        return self._task_matches(task, snapshot, filters)

    def _outbound_delivery_matches(
        self,
        delivery: Any,
        snapshot: OperatorDashboardSnapshot,
        filters: OperatorDashboardFilters,
    ) -> bool:
        if filters.session_id is not None and delivery.session_id != filters.session_id:
            return False
        task = self._task_by_public_task_id(snapshot, delivery.task_id)
        if task is None:
            return filters.session_id is None
        return self._task_matches(task, snapshot, filters)

    def _job_pool_key_for_job_id(
        self,
        snapshot: OperatorDashboardSnapshot,
        job_id: str | None,
    ) -> str | None:
        if job_id is None:
            return None
        return snapshot.job_pool_key_by_id.get(job_id)

    def _task_by_public_task_id(
        self,
        snapshot: OperatorDashboardSnapshot,
        task_id: str,
    ) -> Any | None:
        for task in snapshot.tasks:
            if task.task_id == task_id:
                return task
        return None

    def _filter_pool_diagnostics(
        self,
        pool_diagnostics: dict[str, Any],
        filters: OperatorDashboardFilters,
    ) -> dict[str, Any]:
        if filters.runtime_pool_key is None:
            return pool_diagnostics
        pools = [
            pool
            for pool in pool_diagnostics.get("pools", [])
            if isinstance(pool, dict) and pool.get("pool_key") == filters.runtime_pool_key
        ]
        return {**pool_diagnostics, "pools": pools, "total_pools": len(pools)}

    def _pool_key_by_id(self, pool_diagnostics: dict[str, Any]) -> dict[str, str]:
        pools = pool_diagnostics.get("pools", [])
        if not isinstance(pools, list):
            return {}
        return {
            item["id"]: item["pool_key"]
            for item in pools
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("pool_key"), str)
        }

    def _pool_map(self, pool_diagnostics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        pools = pool_diagnostics.get("pools", [])
        if not isinstance(pools, list):
            return {}
        return {
            item["pool_key"]: item
            for item in pools
            if isinstance(item, dict) and isinstance(item.get("pool_key"), str)
        }

    @staticmethod
    def _earliest(current: str | None, candidate: str | None) -> str | None:
        if current is None:
            return candidate
        if candidate is None:
            return current
        return min(current, candidate)

    @staticmethod
    def _latest(current: str | None, candidate: str | None) -> str | None:
        if current is None:
            return candidate
        if candidate is None:
            return current
        return max(current, candidate)

    @staticmethod
    def _average(values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    def _telemetry_metrics(
        self,
        *,
        snapshot: OperatorDashboardSnapshot,
        dashboard: dict[str, Any],
    ) -> dict[str, Any]:
        queue_depth = sum(
            item["queued_jobs"] + item["running_jobs"] + item["blocked_jobs"]
            for item in dashboard["queue_heat"]
        )
        return {
            "queue_depth": queue_depth,
            "queued_jobs": sum(item["queued_jobs"] for item in dashboard["queue_heat"]),
            "running_jobs": sum(item["running_jobs"] for item in dashboard["queue_heat"]),
            "blocked_jobs": sum(item["blocked_jobs"] for item in dashboard["queue_heat"]),
            "average_job_latency_seconds": self._average_job_latency_seconds(snapshot.jobs),
            "average_phase_duration_seconds": self._average_phase_duration_seconds(
                snapshot.sessions,
                snapshot.phases,
                snapshot.phase_key_by_session_id,
            ),
            "pending_review_bottlenecks": sum(
                item["pending_reviews"] for item in dashboard["review_bottlenecks"]
            ),
            "degraded_runtime_pools": [
                pool["pool_key"]
                for pool in dashboard["runtime_pools"]
                if pool["pool_status"] != "ready"
            ],
            "runtime_pool_pressure": {
                pool["pool_key"]: {
                    "pool_status": pool["pool_status"],
                    "utilization_ratio": pool["utilization_ratio"],
                    "queued_jobs": pool["queued_jobs"],
                    "blocked_jobs": pool["blocked_jobs"],
                    "pending_reviews": pool["pending_reviews"],
                    "pending_tasks": pool["pending_tasks"],
                }
                for pool in dashboard["runtime_pools"]
            },
            "public_task_throughput": dashboard["public_task_throughput"],
            "outbound_webhooks": dashboard["outbound_webhooks"],
        }

    def _average_job_latency_seconds(self, jobs: list[Any]) -> float | None:
        ages = []
        now = datetime.now(timezone.utc)
        for job in jobs:
            started_at = self._parse_timestamp(job.started_at)
            if started_at is None:
                started_at = self._parse_timestamp(job.created_at)
            if started_at is None:
                continue
            if job.status not in {
                "queued",
                "running",
                "input_required",
                "auth_required",
                "paused_by_loop_guard",
            }:
                continue
            ages.append((now - started_at).total_seconds())
        return self._average(ages)

    def _average_phase_duration_seconds(
        self,
        sessions: list[Any],
        phases: list[Any],
        phase_key_by_session_id: dict[str, str | None],
    ) -> float | None:
        phase_by_key = {phase.id: phase for phase in phases}
        ages = []
        now = datetime.now(timezone.utc)
        for session in sessions:
            phase_key = phase_key_by_session_id.get(session.id)
            if phase_key is None or session.active_phase_id is None:
                continue
            phase = phase_by_key.get(session.active_phase_id)
            if phase is None:
                continue
            updated_at = self._parse_timestamp(phase.updated_at)
            if updated_at is None:
                continue
            ages.append((now - updated_at).total_seconds())
        return self._average(ages)

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
