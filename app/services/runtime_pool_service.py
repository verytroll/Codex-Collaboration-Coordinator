"""Runtime pools and work context orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.repositories.agents import AgentRepository, AgentRuntimeRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.runtime_pools import (
    RuntimePoolRecord,
    RuntimePoolRepository,
    WorkContextRecord,
)
from app.services.work_context_service import WorkContextPlan, WorkContextService

ACTIVE_CONTEXT_STATUSES = {"active", "fallback", "recovered"}
DISPATCHABLE_RUNTIME_STATUSES = {"starting", "online", "busy"}
VALID_POOL_STATUSES = {"ready", "degraded", "offline"}
VALID_ISOLATION_MODES = {"shared", "isolated", "ephemeral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class RuntimePoolDefinition:
    """Resolved runtime pool definition."""

    id: str
    pool_key: str
    title: str
    description: str | None
    runtime_kind: str
    preferred_transport_kind: str | None
    required_capabilities: tuple[str, ...]
    fallback_pool_key: str | None
    max_active_contexts: int
    default_isolation_mode: str
    pool_status: str
    metadata: dict[str, Any] | None
    is_default: bool
    sort_order: int
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class RuntimePoolAssignment:
    """Resolved runtime pool assignment for a job."""

    pool: RuntimePoolDefinition
    context: WorkContextRecord | None
    runtime_id: str | None
    fallback_used: bool
    runtime_found: bool
    selection_reason: str | None


@dataclass(frozen=True, slots=True)
class RuntimePoolPlan:
    """Resolved runtime pool assignment plan."""

    pool: RuntimePoolDefinition
    runtime_id: str | None
    workspace_path: str | None
    isolation_mode: str
    context_status: str
    ownership_state: str
    selection_reason: str | None
    fallback_used: bool
    runtime_found: bool
    failure_reason: str | None = None


class RuntimePoolService:
    """Manage runtime pool catalog and assignment to isolated work contexts."""

    _BUILTIN_POOLS: tuple[RuntimePoolDefinition, ...] = (
        RuntimePoolDefinition(
            id="rpl_general_shared",
            pool_key="general_shared",
            title="General Shared",
            description="Default shared execution pool for normal collaborative work.",
            runtime_kind="codex",
            preferred_transport_kind="stdio",
            required_capabilities=(),
            fallback_pool_key=None,
            max_active_contexts=4,
            default_isolation_mode="shared",
            pool_status="ready",
            metadata={"lane": "general"},
            is_default=True,
            sort_order=10,
            created_at="2026-04-01T00:00:00Z",
            updated_at="2026-04-01T00:00:00Z",
        ),
        RuntimePoolDefinition(
            id="rpl_isolated_work",
            pool_key="isolated_work",
            title="Isolated Work",
            description="Dedicated isolated workspace for tasks that should not share state.",
            runtime_kind="codex",
            preferred_transport_kind="stdio",
            required_capabilities=(),
            fallback_pool_key="general_shared",
            max_active_contexts=1,
            default_isolation_mode="isolated",
            pool_status="ready",
            metadata={"lane": "isolated"},
            is_default=False,
            sort_order=20,
            created_at="2026-04-01T00:00:00Z",
            updated_at="2026-04-01T00:00:00Z",
        ),
    )

    def __init__(
        self,
        *,
        runtime_pool_repository: RuntimePoolRepository,
        work_context_service: WorkContextService,
        agent_repository: AgentRepository,
        runtime_repository: AgentRuntimeRepository,
        job_repository: JobRepository,
    ) -> None:
        self.runtime_pool_repository = runtime_pool_repository
        self.work_context_service = work_context_service
        self.agent_repository = agent_repository
        self.runtime_repository = runtime_repository
        self.job_repository = job_repository

    def list_builtin_pools(self) -> list[RuntimePoolDefinition]:
        """Return the built-in runtime pool catalog."""
        return list(self._BUILTIN_POOLS)

    async def list_pools(self) -> list[RuntimePoolDefinition]:
        """Return built-in and stored runtime pools."""
        stored = [
            self._record_to_definition(record)
            for record in await self.runtime_pool_repository.list()
        ]
        return [*self.list_builtin_pools(), *stored]

    async def get_pool(self, pool_key: str) -> RuntimePoolDefinition:
        """Return a pool by key."""
        for pool in self._BUILTIN_POOLS:
            if pool.pool_key == pool_key:
                return pool
        record = await self.runtime_pool_repository.get_by_key(pool_key)
        if record is None:
            raise LookupError(f"Runtime pool not found: {pool_key}")
        return self._record_to_definition(record)

    async def create_pool(
        self,
        *,
        pool_key: str,
        title: str,
        description: str | None = None,
        runtime_kind: str = "codex",
        preferred_transport_kind: str | None = None,
        required_capabilities: list[str] | None = None,
        fallback_pool_key: str | None = None,
        max_active_contexts: int = 1,
        default_isolation_mode: str = "isolated",
        pool_status: str = "ready",
        metadata: dict[str, Any] | None = None,
        is_default: bool = False,
        sort_order: int = 100,
    ) -> RuntimePoolDefinition:
        """Create a custom runtime pool."""
        if not pool_key.strip():
            raise ValueError("Runtime pool key cannot be empty")
        if not title.strip():
            raise ValueError("Runtime pool title cannot be empty")
        if max_active_contexts < 0:
            raise ValueError("Runtime pool max_active_contexts must be greater than or equal to 0")
        if default_isolation_mode not in VALID_ISOLATION_MODES:
            raise ValueError(
                f"Unsupported runtime pool isolation mode: {default_isolation_mode}"
            )
        if pool_status not in VALID_POOL_STATUSES:
            raise ValueError(f"Unsupported runtime pool status: {pool_status}")
        if pool_key in self._builtin_pool_keys():
            raise ValueError(f"Runtime pool key is reserved for built-ins: {pool_key}")
        if await self.runtime_pool_repository.get_by_key(pool_key) is not None:
            raise ValueError(f"Runtime pool already exists: {pool_key}")
        if fallback_pool_key is not None:
            await self.get_pool(fallback_pool_key)

        now = _utc_now()
        record = RuntimePoolRecord(
            id=f"rpl_{uuid4().hex}",
            pool_key=pool_key,
            title=title,
            description=description,
            runtime_kind=runtime_kind,
            preferred_transport_kind=preferred_transport_kind,
            required_capabilities_json=(
                json.dumps(sorted(required_capabilities or []), sort_keys=True)
                if required_capabilities is not None
                else None
            ),
            fallback_pool_key=fallback_pool_key,
            max_active_contexts=max_active_contexts,
            default_isolation_mode=default_isolation_mode,
            pool_status=pool_status,
            metadata_json=json.dumps(metadata, sort_keys=True) if metadata is not None else None,
            is_default=1 if is_default else 0,
            sort_order=sort_order,
            created_at=now,
            updated_at=now,
        )
        saved = await self.runtime_pool_repository.create(record)
        return self._record_to_definition(saved)

    async def assign_work_context_for_job(
        self,
        job: JobRecord,
        *,
        preferred_pool_key: str | None = None,
        required_capabilities: list[str] | None = None,
        runtime_id: str | None = None,
    ) -> RuntimePoolAssignment:
        """Assign a job into a pool and persist its work context."""
        plan = await self.plan_assignment(
            job_id=job.id,
            session_id=job.session_id,
            agent_id=job.assigned_agent_id,
            preferred_pool_key=preferred_pool_key,
            required_capabilities=required_capabilities,
            runtime_id=runtime_id,
        )
        context = await self.work_context_service.create_or_update_context(
            job_id=job.id,
            session_id=job.session_id,
            agent_id=job.assigned_agent_id,
            plan=WorkContextPlan(
                runtime_pool_id=plan.pool.id,
                runtime_id=plan.runtime_id,
                workspace_path=plan.workspace_path,
                isolation_mode=plan.isolation_mode,
                context_status=plan.context_status,
                ownership_state=plan.ownership_state,
                selection_reason=plan.selection_reason,
                failure_reason=plan.failure_reason,
            ),
        )
        return RuntimePoolAssignment(
            pool=plan.pool,
            context=context,
            runtime_id=plan.runtime_id,
            fallback_used=plan.fallback_used,
            runtime_found=plan.runtime_found,
            selection_reason=plan.selection_reason,
        )

    async def plan_assignment(
        self,
        *,
        job_id: str,
        session_id: str,
        agent_id: str,
        preferred_pool_key: str | None = None,
        required_capabilities: list[str] | None = None,
        runtime_id: str | None = None,
    ) -> RuntimePoolPlan:
        """Resolve the best pool/runtime combination for a job."""
        agent = await self.agent_repository.get(agent_id)
        if agent is None:
            raise LookupError(f"Agent not found: {agent_id}")

        pools = await self.list_pools()
        selected_pool, fallback_used, selection_reason = await self._select_pool(
            pools,
            preferred_pool_key=preferred_pool_key,
            agent_capabilities=self._parse_capabilities(agent.capabilities_json),
            required_capabilities=self._normalize_capabilities(required_capabilities),
        )
        runtime = await self._resolve_runtime(agent_id, selected_pool.runtime_kind)
        if runtime_id is not None:
            explicit_runtime = await self.runtime_repository.get(runtime_id)
            if explicit_runtime is not None and explicit_runtime.agent_id == agent_id:
                runtime = explicit_runtime
        runtime_found = runtime is not None
        runtime_id = runtime.id if runtime is not None else None
        workspace_path = self._build_workspace_path(runtime, selected_pool, session_id, job_id)
        context_status = self._context_status(runtime, fallback_used)
        ownership_state = "borrowed" if fallback_used else "owned"
        failure_reason = None
        if runtime is None:
            selection_reason = selection_reason or "No runtime available for selected pool."
        return RuntimePoolPlan(
            pool=selected_pool,
            runtime_id=runtime_id,
            workspace_path=workspace_path,
            isolation_mode=selected_pool.default_isolation_mode,
            context_status=context_status,
            ownership_state=ownership_state,
            selection_reason=selection_reason,
            fallback_used=fallback_used,
            runtime_found=runtime_found,
            failure_reason=failure_reason,
        )

    async def recover_work_context(self, context_id: str) -> WorkContextRecord:
        """Recover a persisted work context through the context service."""
        return await self.work_context_service.recover_context(context_id)

    async def get_contexts(self) -> list[WorkContextRecord]:
        """Return all work contexts."""
        return await self.work_context_service.list_contexts()

    async def get_pool_diagnostics(self) -> dict[str, Any]:
        """Return aggregate runtime pool diagnostics."""
        pools = await self.list_pools()
        contexts = await self.work_context_service.list_contexts()
        runtimes = await self.runtime_repository.list()
        pool_responses = [
            self._pool_response(
                pool,
                contexts=contexts,
                runtimes=runtimes,
            )
            for pool in pools
        ]
        return {
            "generated_at": _utc_now(),
            "total_pools": len(pools),
            "total_contexts": len(contexts),
            "owned_contexts": sum(1 for context in contexts if context.ownership_state == "owned"),
            "borrowed_contexts": sum(
                1 for context in contexts if context.ownership_state == "borrowed"
            ),
            "released_contexts": sum(
                1 for context in contexts if context.ownership_state == "released"
            ),
            "pools": pool_responses,
        }

    def _builtin_pool_keys(self) -> set[str]:
        return {pool.pool_key for pool in self._BUILTIN_POOLS}

    async def _select_pool(
        self,
        pools: list[RuntimePoolDefinition],
        *,
        preferred_pool_key: str | None,
        agent_capabilities: dict[str, bool],
        required_capabilities: list[str],
    ) -> tuple[RuntimePoolDefinition, bool, str | None]:
        visited: set[str] = set()
        selected = None
        if preferred_pool_key is not None:
            selected = next((pool for pool in pools if pool.pool_key == preferred_pool_key), None)
        if selected is None:
            selected = next((pool for pool in pools if pool.is_default), None)
        if selected is None and pools:
            selected = pools[0]
        if selected is None:
            raise LookupError("No runtime pools available.")

        reason = f"Selected pool {selected.pool_key}."
        fallback_used = False
        while True:
            if selected.pool_key in visited:
                break
            visited.add(selected.pool_key)
            if self._pool_supports_capabilities(
                selected,
                agent_capabilities,
                required_capabilities,
            ) and not await self._pool_is_at_capacity(selected):
                break
            fallback_pool_key = selected.fallback_pool_key
            fallback_pool = (
                next((pool for pool in pools if pool.pool_key == fallback_pool_key), None)
                if fallback_pool_key is not None
                else None
            )
            if fallback_pool is None or fallback_pool.pool_key in visited:
                default_pool = next((pool for pool in pools if pool.is_default), None)
                if default_pool is None or default_pool.pool_key in visited:
                    break
                fallback_pool = default_pool
            if fallback_pool.pool_key != selected.pool_key:
                selected = fallback_pool
                fallback_used = True
                if not self._pool_supports_capabilities(
                    selected,
                    agent_capabilities,
                    required_capabilities,
                ):
                    reason = (
                        f"Fallback to pool {selected.pool_key} because capabilities were missing."
                    )
                else:
                    reason = (
                        f"Fallback to pool {selected.pool_key} because the selected pool is full."
                    )
                continue
            break

        return selected, fallback_used, reason

    async def _pool_is_at_capacity(self, pool: RuntimePoolDefinition) -> bool:
        if pool.max_active_contexts <= 0:
            return False
        contexts = await self.work_context_service.list_by_pool(pool.id)
        active = sum(1 for context in contexts if context.context_status in ACTIVE_CONTEXT_STATUSES)
        return active >= pool.max_active_contexts

    def _pool_supports_capabilities(
        self,
        pool: RuntimePoolDefinition,
        agent_capabilities: dict[str, bool],
        required_capabilities: list[str],
    ) -> bool:
        required = set(pool.required_capabilities)
        required.update(required_capabilities)
        return all(agent_capabilities.get(capability, False) for capability in required)

    async def _resolve_runtime(
        self,
        agent_id: str,
        runtime_kind: str,
    ) -> Any | None:
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
        runtime: Any | None,
        pool: RuntimePoolDefinition,
        session_id: str,
        job_id: str,
    ) -> str | None:
        base_path = None
        if runtime is not None and getattr(runtime, "workspace_path", None) is not None:
            base_path = runtime.workspace_path
        elif pool.metadata is not None:
            base_path = pool.metadata.get("workspace_root")
        if base_path is None:
            return None
        return str(Path(base_path) / ".codex" / session_id / job_id)

    def _context_status(
        self,
        runtime: Any | None,
        fallback_used: bool,
    ) -> str:
        if runtime is None:
            return "waiting_for_runtime"
        if fallback_used:
            return "fallback"
        return "active"

    def _record_to_definition(self, record: RuntimePoolRecord) -> RuntimePoolDefinition:
        return RuntimePoolDefinition(
            id=record.id,
            pool_key=record.pool_key,
            title=record.title,
            description=record.description,
            runtime_kind=record.runtime_kind,
            preferred_transport_kind=record.preferred_transport_kind,
            required_capabilities=tuple(self._parse_string_list(record.required_capabilities_json)),
            fallback_pool_key=record.fallback_pool_key,
            max_active_contexts=record.max_active_contexts,
            default_isolation_mode=record.default_isolation_mode,
            pool_status=record.pool_status,
            metadata=self._parse_metadata(record.metadata_json),
            is_default=bool(record.is_default),
            sort_order=record.sort_order,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _pool_utilization_counts(
        self,
        pool_id: str,
        runtime_kind: str,
        contexts: list[WorkContextRecord],
        runtimes: list[Any],
    ) -> tuple[int, int, int, int]:
        matching_contexts = [context for context in contexts if context.runtime_pool_id == pool_id]
        active_contexts = sum(
            1 for context in matching_contexts if context.context_status in ACTIVE_CONTEXT_STATUSES
        )
        waiting_contexts = sum(
            1 for context in matching_contexts if context.context_status == "waiting_for_runtime"
        )
        borrowed_contexts = sum(
            1 for context in matching_contexts if context.ownership_state == "borrowed"
        )
        available_runtimes = sum(
            1
            for runtime in runtimes
            if runtime.runtime_kind == runtime_kind
            and runtime.runtime_status in DISPATCHABLE_RUNTIME_STATUSES
        )
        return active_contexts, waiting_contexts, borrowed_contexts, available_runtimes

    def _pool_response(
        self,
        pool: RuntimePoolDefinition,
        *,
        contexts: list[WorkContextRecord],
        runtimes: list[Any],
    ) -> dict[str, Any]:
        active_contexts, waiting_contexts, borrowed_contexts, available_runtimes = (
            self._pool_utilization_counts(pool.id, pool.runtime_kind, contexts, runtimes)
        )
        utilization_ratio = (
            active_contexts / pool.max_active_contexts if pool.max_active_contexts > 0 else 0.0
        )
        return {
            "id": pool.id,
            "pool_key": pool.pool_key,
            "title": pool.title,
            "description": pool.description,
            "runtime_kind": pool.runtime_kind,
            "preferred_transport_kind": pool.preferred_transport_kind,
            "required_capabilities": list(pool.required_capabilities),
            "fallback_pool_key": pool.fallback_pool_key,
            "max_active_contexts": pool.max_active_contexts,
            "default_isolation_mode": pool.default_isolation_mode,
            "pool_status": pool.pool_status,
            "metadata": pool.metadata,
            "is_default": pool.is_default,
            "sort_order": pool.sort_order,
            "active_context_count": active_contexts,
            "waiting_context_count": waiting_contexts,
            "borrowed_context_count": borrowed_contexts,
            "available_runtime_count": available_runtimes,
            "utilization_ratio": utilization_ratio,
            "created_at": pool.created_at,
            "updated_at": pool.updated_at,
        }

    @staticmethod
    def _parse_string_list(payload_json: str | None) -> list[str]:
        if payload_json is None:
            return []
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, str)]

    @staticmethod
    def _parse_metadata(payload_json: str | None) -> dict[str, Any] | None:
        if payload_json is None:
            return None
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _parse_capabilities(self, payload_json: str | None) -> dict[str, bool]:
        if payload_json is None:
            return {}
        payload = self._parse_metadata(payload_json)
        if payload is None:
            return {}
        return {key: bool(value) for key, value in payload.items()}

    @staticmethod
    def _normalize_capabilities(capabilities: list[str] | None) -> list[str]:
        if capabilities is None:
            return []
        return [
            capability
            for capability in capabilities
            if isinstance(capability, str) and capability
        ]
