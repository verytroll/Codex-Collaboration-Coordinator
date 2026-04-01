"""System status aggregation for coordinator diagnostics."""

from __future__ import annotations

import asyncio
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from app.codex_bridge.process_manager import CodexProcessManager
from app.db.connection import connect_sqlite
from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.approvals import ApprovalRepository
from app.repositories.jobs import JobRepository
from app.repositories.sessions import SessionRepository


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
    ) -> None:
        self.database_url = database_url
        self.codex_bridge_mode = codex_bridge_mode
        self.session_repository = session_repository
        self.agent_repository = agent_repository
        self.runtime_repository = runtime_repository
        self.job_repository = job_repository
        self.approval_repository = approval_repository

    async def get_status(self) -> dict[str, Any]:
        """Return a system status payload suitable for the API model."""
        db_check = await self._check_database()
        bridge_check = self._check_codex_bridge()
        diagnostics: list[str] = []
        aggregates = self._empty_aggregates()

        if db_check["status"] == "ok":
            aggregates = await self._load_aggregates()
            diagnostics.extend(self._build_diagnostics(bridge_check, aggregates))
        else:
            diagnostics.append(db_check["detail"] or "Database unavailable.")

        return {
            "status": self._overall_status(db_check["status"], bridge_check["status"], diagnostics),
            "checks": {
                "db": db_check,
                "codex_bridge": bridge_check,
            },
            "aggregates": aggregates,
            "diagnostics": diagnostics,
        }

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
        sessions, agents, runtimes, jobs, approvals = await asyncio.gather(
            self.session_repository.list(),
            self.agent_repository.list(),
            self.runtime_repository.list(),
            self.job_repository.list(),
            self.approval_repository.list(),
        )
        return {
            "active_sessions": sum(1 for session in sessions if session.status == "active"),
            "registered_agents": len(agents),
            "jobs": self._job_counts(jobs),
            "pending_approvals": sum(1 for approval in approvals if approval.status == "pending"),
            "runtimes_by_status": dict(
                sorted(Counter(runtime.runtime_status for runtime in runtimes).items())
            ),
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
            "runtimes_by_status": {},
        }
