"""Detailed debug surface for operators."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.agents import AgentRuntimeRepository
from app.repositories.approvals import ApprovalRepository
from app.repositories.jobs import JobRepository
from app.repositories.sessions import SessionRepository
from app.services.system_status import SystemStatusService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class DebugService:
    """Build a compact debug surface without requiring direct DB access."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        runtime_repository: AgentRuntimeRepository,
        job_repository: JobRepository,
        approval_repository: ApprovalRepository,
        system_status_service: SystemStatusService,
    ) -> None:
        self.session_repository = session_repository
        self.runtime_repository = runtime_repository
        self.job_repository = job_repository
        self.approval_repository = approval_repository
        self.system_status_service = system_status_service

    async def get_surface(self) -> dict[str, Any]:
        """Return a detailed diagnostics payload for operators."""
        status = await self.system_status_service.get_status()
        if status["checks"]["db"]["status"] != "ok":
            return {
                "generated_at": _utc_now(),
                "codex_bridge": status["checks"]["codex_bridge"],
                "runtime_statuses": {},
                "active_sessions": [],
                "queued_jobs": [],
                "running_jobs": [],
                "blocked_jobs": [],
                "pending_approvals": [],
                "diagnostics": status["diagnostics"],
            }

        sessions = await self.session_repository.list()
        runtimes = await self.runtime_repository.list()
        jobs = await self.job_repository.list()
        approvals = await self.approval_repository.list()
        return {
            "generated_at": _utc_now(),
            "codex_bridge": status["checks"]["codex_bridge"],
            "runtime_statuses": status["aggregates"]["runtimes_by_status"],
            "active_sessions": [
                self._session_item(session) for session in sessions if session.status == "active"
            ],
            "queued_jobs": [self._job_item(job) for job in jobs if job.status == "queued"],
            "running_jobs": [self._job_item(job) for job in jobs if job.status == "running"],
            "blocked_jobs": [
                self._job_item(job)
                for job in jobs
                if job.status in {"input_required", "auth_required", "paused_by_loop_guard"}
            ],
            "pending_approvals": [
                self._approval_item(approval)
                for approval in approvals
                if approval.status == "pending"
            ],
            "diagnostics": status["diagnostics"] + self._runtime_diagnostics(runtimes),
        }

    def _session_item(self, session: Any) -> dict[str, Any]:
        return {
            "id": session.id,
            "title": session.title,
            "status": session.status,
            "lead_agent_id": session.lead_agent_id,
            "updated_at": session.updated_at,
            "last_message_at": session.last_message_at,
        }

    def _job_item(self, job: Any) -> dict[str, Any]:
        return {
            "id": job.id,
            "session_id": job.session_id,
            "assigned_agent_id": job.assigned_agent_id,
            "title": job.title,
            "status": job.status,
            "priority": job.priority,
            "codex_thread_id": job.codex_thread_id,
            "active_turn_id": job.active_turn_id,
            "last_known_turn_status": job.last_known_turn_status,
            "updated_at": job.updated_at,
        }

    def _approval_item(self, approval: Any) -> dict[str, Any]:
        return {
            "id": approval.id,
            "job_id": approval.job_id,
            "agent_id": approval.agent_id,
            "approval_type": approval.approval_type,
            "status": approval.status,
            "requested_at": approval.requested_at,
            "updated_at": approval.updated_at,
        }

    def _runtime_diagnostics(self, runtimes: list[Any]) -> list[str]:
        if not runtimes:
            return []
        stale = [runtime.id for runtime in runtimes if runtime.last_heartbeat_at is None]
        if not stale:
            return []
        return [f"{len(stale)} runtime(s) have no heartbeat timestamp."]
