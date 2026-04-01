"""System status aggregation for coordinator diagnostics."""

from __future__ import annotations

import asyncio
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.codex_bridge.process_manager import CodexProcessManager
from app.core.logging import bind_log_context, get_logger, reset_log_context
from app.core.telemetry import get_telemetry_service
from app.db.connection import connect_sqlite
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.approvals import ApprovalRepository
from app.repositories.jobs import JobRepository
from app.repositories.phases import PhaseRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.sessions import SessionRepository

logger = get_logger(__name__)


class SystemStatusService:
    """Build operator-facing status aggregates for the coordinator."""

    def __init__(
        self,
        *,
        database_url: str,
        codex_bridge_mode: str,
        session_repository: SessionRepository,
        agent_repository: AgentRepository,
        runtime_repository: AgentRuntimeRepository,
        job_repository: JobRepository,
        approval_repository: ApprovalRepository,
        phase_repository: PhaseRepository,
        review_repository: ReviewRepository,
    ) -> None:
        self.database_url = database_url
        self.codex_bridge_mode = codex_bridge_mode
        self.session_repository = session_repository
        self.agent_repository = agent_repository
        self.runtime_repository = runtime_repository
        self.job_repository = job_repository
        self.approval_repository = approval_repository
        self.phase_repository = phase_repository
        self.review_repository = review_repository

    async def get_status(self) -> dict[str, Any]:
        """Return a system status payload suitable for the API model."""
        log_tokens = bind_log_context(event_type="system.status")
        db_check = await self._check_database()
        bridge_check = self._check_codex_bridge()
        diagnostics: list[str] = []
        aggregates = self._empty_aggregates()
        if db_check["status"] == "ok":
            aggregates = await self._load_aggregates()
            diagnostics.extend(self._build_diagnostics(bridge_check, aggregates))
        else:
            diagnostics.append(db_check["detail"] or "Database unavailable.")

        payload = {
            "status": self._overall_status(db_check["status"], bridge_check["status"], diagnostics),
            "checks": {
                "db": db_check,
                "codex_bridge": bridge_check,
            },
            "aggregates": aggregates,
            "diagnostics": diagnostics,
            "telemetry": {},
        }
        await get_telemetry_service().record_sample(
            "system_status",
            metrics=self._telemetry_metrics(aggregates=aggregates, bridge_check=bridge_check),
        )
        telemetry = await get_telemetry_service().get_surface()
        payload["telemetry"] = telemetry
        logger.info("system status generated")
        reset_log_context(log_tokens)
        return payload

    async def _check_database(self) -> dict[str, str]:
        try:
            await asyncio.to_thread(self._probe_database_sync)
        except Exception as exc:
            return {"status": "unavailable", "detail": f"Database check failed: {exc}"}
        return {"status": "ok", "detail": "SQLite reachable."}

    def _probe_database_sync(self) -> None:
        connection = connect_sqlite(self.database_url)
        try:
            connection.execute("SELECT 1").fetchone()
        finally:
            connection.close()

    async def _load_aggregates(self) -> dict[str, Any]:
        sessions, agents, runtimes, jobs, approvals, phases, reviews = await asyncio.gather(
            self.session_repository.list(),
            self.agent_repository.list(),
            self.runtime_repository.list(),
            self.job_repository.list(),
            self.approval_repository.list(),
            self.phase_repository.list(),
            self.review_repository.list(),
        )
        return {
            "active_sessions": sum(1 for session in sessions if session.status == "active"),
            "registered_agents": len(agents),
            "jobs": self._job_counts(jobs),
            "pending_approvals": sum(1 for approval in approvals if approval.status == "pending"),
            "pending_reviews": sum(1 for review in reviews if review.review_status == "requested"),
            "runtimes_by_status": dict(
                sorted(Counter(runtime.runtime_status for runtime in runtimes).items())
            ),
            "active_phase_durations": self._active_phase_durations(sessions, phases),
            "average_job_latency_seconds": self._average_job_latency_seconds(jobs),
            "average_review_wait_seconds": self._average_review_wait_seconds(reviews),
        }

    def _check_codex_bridge(self) -> dict[str, str]:
        manager = CodexProcessManager()
        executable = manager.command[0] if manager.command else "codex"
        resolved = self._resolve_command(executable)
        if resolved is None:
            return {
                "status": "degraded",
                "detail": (
                    f"CodexBridge mode={self.codex_bridge_mode}; command not found: {executable}"
                ),
            }
        return {
            "status": "ok",
            "detail": f"CodexBridge mode={self.codex_bridge_mode}; command={resolved}",
        }

    def _resolve_command(self, executable: str) -> str | None:
        candidate = Path(executable)
        if candidate.is_file():
            return str(candidate)
        return shutil.which(executable)

    def _job_counts(self, jobs: list[Any]) -> dict[str, int]:
        counts = Counter(job.status for job in jobs)
        return {
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "input_required": counts.get("input_required", 0),
            "auth_required": counts.get("auth_required", 0),
            "paused_by_loop_guard": counts.get("paused_by_loop_guard", 0),
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "canceled": counts.get("canceled", 0),
        }

    def _build_diagnostics(
        self,
        bridge_check: dict[str, str],
        aggregates: dict[str, Any],
    ) -> list[str]:
        diagnostics: list[str] = []
        if bridge_check["status"] != "ok":
            diagnostics.append(bridge_check["detail"] or "CodexBridge unavailable.")
        jobs = aggregates["jobs"]
        if jobs["queued"] > 0:
            diagnostics.append(f"{jobs['queued']} queued job(s) waiting for execution.")
        if jobs["input_required"] > 0 or jobs["auth_required"] > 0:
            blocked = jobs["input_required"] + jobs["auth_required"]
            diagnostics.append(f"{blocked} job(s) waiting for input or approval.")
        if jobs["paused_by_loop_guard"] > 0:
            diagnostics.append(f"{jobs['paused_by_loop_guard']} job(s) paused by loop guard.")
        if jobs["failed"] > 0:
            diagnostics.append(f"{jobs['failed']} job(s) failed and may need intervention.")
        if aggregates["pending_approvals"] > 0:
            diagnostics.append(
                f"{aggregates['pending_approvals']} approval request(s) pending operator action."
            )
        offline = aggregates["runtimes_by_status"].get("offline", 0)
        crashed = aggregates["runtimes_by_status"].get("crashed", 0)
        if crashed > 0:
            diagnostics.append(f"{crashed} runtime(s) marked crashed.")
        if offline > 0:
            diagnostics.append(f"{offline} runtime(s) marked offline.")
        return diagnostics

    def _overall_status(
        self,
        db_status: str,
        bridge_status: str,
        diagnostics: list[str],
    ) -> str:
        if db_status == "unavailable":
            return "unavailable"
        if bridge_status != "ok" or diagnostics:
            return "degraded"
        return "ok"

    def _empty_aggregates(self) -> dict[str, Any]:
        return {
            "active_sessions": 0,
            "registered_agents": 0,
            "jobs": self._job_counts([]),
            "pending_approvals": 0,
            "pending_reviews": 0,
            "runtimes_by_status": {},
            "active_phase_durations": {},
            "average_job_latency_seconds": None,
            "average_review_wait_seconds": None,
        }

    def _telemetry_metrics(
        self,
        *,
        aggregates: dict[str, Any],
        bridge_check: dict[str, str],
    ) -> dict[str, Any]:
        queue_depth = (
            aggregates["jobs"]["queued"]
            + aggregates["jobs"]["running"]
            + aggregates["jobs"]["input_required"]
            + aggregates["jobs"]["auth_required"]
            + aggregates["jobs"]["paused_by_loop_guard"]
        )
        phase_durations = aggregates.get("active_phase_durations", {})
        return {
            "queue_depth": queue_depth,
            "queued_jobs": aggregates["jobs"]["queued"],
            "running_jobs": aggregates["jobs"]["running"],
            "pending_approvals": aggregates["pending_approvals"],
            "pending_reviews": aggregates.get("pending_reviews", 0),
            "pending_review_bottlenecks": aggregates.get("pending_reviews", 0),
            "average_job_latency_seconds": aggregates.get("average_job_latency_seconds"),
            "average_phase_duration_seconds": self._average_of_mapping(phase_durations),
            "average_review_wait_seconds": aggregates.get("average_review_wait_seconds"),
            "codex_bridge_status": bridge_check["status"],
        }

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if value is None:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

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

    def _average_review_wait_seconds(self, reviews: list[Any]) -> float | None:
        ages = []
        now = datetime.now(timezone.utc)
        for review in reviews:
            if review.review_status != "requested":
                continue
            requested_at = self._parse_timestamp(review.requested_at)
            if requested_at is None:
                continue
            ages.append((now - requested_at).total_seconds())
        return self._average(ages)

    def _active_phase_durations(self, sessions: list[Any], phases: list[Any]) -> dict[str, float]:
        phase_by_id = {phase.id: phase for phase in phases}
        durations: dict[str, list[float]] = {}
        now = datetime.now(timezone.utc)
        for session in sessions:
            if session.active_phase_id is None:
                continue
            phase = phase_by_id.get(session.active_phase_id)
            if phase is None:
                continue
            updated_at = self._parse_timestamp(phase.updated_at)
            if updated_at is None:
                continue
            durations.setdefault(phase.phase_key, []).append((now - updated_at).total_seconds())
        return {
            phase_key: round(self._average(values), 2)
            for phase_key, values in durations.items()
            if self._average(values) is not None
        }

    @staticmethod
    def _average(values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    def _average_of_mapping(self, mapping: dict[str, float]) -> float | None:
        values = list(mapping.values())
        return self._average(values) if values else None
