"""Work context persistence and recovery."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.repositories.agents import AgentRepository, AgentRuntimeRecord, AgentRuntimeRepository
from app.repositories.runtime_pools import WorkContextRecord, WorkContextRepository

DISPATCHABLE_RUNTIME_STATUSES = {"starting", "online", "busy"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class WorkContextService:
    """Manage isolated work contexts for jobs."""

    def __init__(
        self,
        *,
        work_context_repository: WorkContextRepository,
        runtime_repository: AgentRuntimeRepository,
        agent_repository: AgentRepository,
    ) -> None:
        self.work_context_repository = work_context_repository
        self.runtime_repository = runtime_repository
        self.agent_repository = agent_repository

    async def get_context(self, context_id: str) -> WorkContextRecord | None:
        """Fetch a work context by identifier."""
        return await self.work_context_repository.get(context_id)

    async def get_by_job(self, job_id: str) -> WorkContextRecord | None:
        """Fetch a work context by job identifier."""
        return await self.work_context_repository.get_by_job(job_id)

    async def list_contexts(self) -> list[WorkContextRecord]:
        """Return all work contexts."""
        return await self.work_context_repository.list()

    async def list_by_session(self, session_id: str) -> list[WorkContextRecord]:
        """Return work contexts for a session."""
        return await self.work_context_repository.list_by_session(session_id)

    async def list_by_pool(self, runtime_pool_id: str) -> list[WorkContextRecord]:
        """Return work contexts bound to a runtime pool."""
        return await self.work_context_repository.list_by_pool(runtime_pool_id)

    async def create_or_update_context(
        self,
        *,
        job_id: str,
        session_id: str,
        agent_id: str,
        plan: WorkContextPlan,
    ) -> WorkContextRecord:
        """Persist the resolved context plan for a job."""
        existing = await self.work_context_repository.get_by_job(job_id)
        now = _utc_now()
        record = WorkContextRecord(
            id=existing.id if existing is not None else f"wcx_{uuid4().hex}",
            session_id=session_id,
            job_id=job_id,
            agent_id=agent_id,
            runtime_pool_id=plan.runtime_pool_id,
            runtime_id=plan.runtime_id,
            context_key=existing.context_key if existing is not None else f"ctx_{job_id}",
            workspace_path=plan.workspace_path,
            isolation_mode=plan.isolation_mode,
            context_status=plan.context_status,
            ownership_state=plan.ownership_state,
            selection_reason=plan.selection_reason,
            failure_reason=plan.failure_reason,
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        if existing is None:
            return await self.work_context_repository.create(record)
        return await self.work_context_repository.update(record)

    async def recover_context(self, context_id: str) -> WorkContextRecord:
        """Try to rebind a context to a live runtime."""
        context = await self.work_context_repository.get(context_id)
        if context is None:
            raise LookupError(f"Work context not found: {context_id}")

        agent = await self.agent_repository.get(context.agent_id)
        if agent is None:
            raise LookupError(f"Agent not found: {context.agent_id}")

        runtime = await self._resolve_runtime(context.agent_id, agent.runtime_kind)
        if runtime is None:
            return context

        updated = replace(
            context,
            runtime_id=runtime.id,
            workspace_path=context.workspace_path
            or self._build_workspace_path(runtime, context.session_id, context.job_id),
            context_status="recovered" if context.context_status != "active" else "active",
            ownership_state=context.ownership_state
            if context.ownership_state == "borrowed"
            else "owned",
            failure_reason=None,
            updated_at=_utc_now(),
        )
        return await self.work_context_repository.update(updated)

    async def _resolve_runtime(
        self,
        agent_id: str,
        runtime_kind: str,
    ) -> AgentRuntimeRecord | None:
        runtimes = await self.runtime_repository.list()
        matching = [
            runtime
            for runtime in runtimes
            if runtime.agent_id == agent_id and runtime.runtime_kind == runtime_kind
        ]
        dispatchable = [
            runtime
            for runtime in matching
            if runtime.runtime_status in DISPATCHABLE_RUNTIME_STATUSES
        ]
        if dispatchable:
            return max(dispatchable, key=lambda runtime: (runtime.created_at, runtime.id))
        if matching:
            return max(matching, key=lambda runtime: (runtime.created_at, runtime.id))
        return None

    def _build_workspace_path(
        self,
        runtime: AgentRuntimeRecord,
        session_id: str,
        job_id: str,
    ) -> str | None:
        if runtime.workspace_path is None:
            return None
        return str(Path(runtime.workspace_path) / ".codex" / session_id / job_id)


@dataclass(frozen=True, slots=True)
class WorkContextPlan:
    """Resolved context plan before persistence."""

    runtime_pool_id: str
    runtime_id: str | None
    workspace_path: str | None
    isolation_mode: str
    context_status: str
    ownership_state: str
    selection_reason: str | None
    failure_reason: str | None
