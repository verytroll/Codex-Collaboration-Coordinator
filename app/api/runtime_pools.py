"""Runtime pool and work context API routes."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_job_repository,
    get_runtime_pool_service,
    get_work_context_service,
)
from app.models.api.runtime_pools import (
    RuntimePoolAssignEnvelope,
    RuntimePoolAssignRequest,
    RuntimePoolCreateRequest,
    RuntimePoolDiagnosticsEnvelope,
    RuntimePoolDiagnosticsResponse,
    RuntimePoolEnvelope,
    RuntimePoolListEnvelope,
    RuntimePoolResponse,
    WorkContextEnvelope,
    WorkContextListEnvelope,
    WorkContextRecoverRequest,
    WorkContextResponse,
)
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.runtime_pools import WorkContextRecord
from app.services.runtime_pool_service import RuntimePoolDefinition, RuntimePoolService
from app.services.work_context_service import WorkContextService

router = APIRouter(prefix="/api/v1", tags=["runtime-pools"])


def _pool_response(
    pool: RuntimePoolDefinition, diagnostics: dict[str, dict[str, Any]]
) -> RuntimePoolResponse:
    pool_diagnostics = diagnostics.get(pool.pool_key, {})
    return RuntimePoolResponse(
        id=pool.id,
        pool_key=pool.pool_key,
        title=pool.title,
        description=pool.description,
        runtime_kind=pool.runtime_kind,
        preferred_transport_kind=pool.preferred_transport_kind,
        required_capabilities=list(pool.required_capabilities),
        fallback_pool_key=pool.fallback_pool_key,
        max_active_contexts=pool.max_active_contexts,
        default_isolation_mode=cast(Any, pool.default_isolation_mode),
        pool_status=cast(Any, pool.pool_status),
        metadata=pool.metadata,
        is_default=pool.is_default,
        sort_order=pool.sort_order,
        active_context_count=int(pool_diagnostics.get("active_context_count", 0)),
        waiting_context_count=int(pool_diagnostics.get("waiting_context_count", 0)),
        borrowed_context_count=int(pool_diagnostics.get("borrowed_context_count", 0)),
        available_runtime_count=int(pool_diagnostics.get("available_runtime_count", 0)),
        utilization_ratio=float(pool_diagnostics.get("utilization_ratio", 0.0)),
        created_at=pool.created_at,
        updated_at=pool.updated_at,
    )


def _pool_diagnostics_map(diagnostics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pools = diagnostics.get("pools", [])
    if not isinstance(pools, list):
        return {}
    return {
        item["pool_key"]: item
        for item in pools
        if isinstance(item, dict) and isinstance(item.get("pool_key"), str)
    }


def _context_response(
    context: WorkContextRecord,
    *,
    pool_key: str,
) -> WorkContextResponse:
    return WorkContextResponse(
        id=context.id,
        session_id=context.session_id,
        job_id=context.job_id,
        agent_id=context.agent_id,
        runtime_pool_key=pool_key,
        runtime_id=context.runtime_id,
        context_key=context.context_key,
        workspace_path=context.workspace_path,
        isolation_mode=cast(Any, context.isolation_mode),
        context_status=cast(Any, context.context_status),
        ownership_state=cast(Any, context.ownership_state),
        selection_reason=context.selection_reason,
        failure_reason=context.failure_reason,
        created_at=context.created_at,
        updated_at=context.updated_at,
    )


async def _load_job(job_repository: JobRepository, job_id: str) -> JobRecord:
    job = await job_repository.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}"
        )
    return job


@router.get("/runtime-pools", response_model=RuntimePoolListEnvelope)
async def list_runtime_pools(
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
) -> RuntimePoolListEnvelope:
    diagnostics = _pool_diagnostics_map(await runtime_pool_service.get_pool_diagnostics())
    pools = [_pool_response(pool, diagnostics) for pool in await runtime_pool_service.list_pools()]
    return RuntimePoolListEnvelope(pools=pools)


@router.get("/runtime-pools/diagnostics", response_model=RuntimePoolDiagnosticsEnvelope)
async def get_runtime_pool_diagnostics(
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
) -> RuntimePoolDiagnosticsEnvelope:
    diagnostics = await runtime_pool_service.get_pool_diagnostics()
    pool_map = _pool_diagnostics_map(diagnostics)
    pool_responses = [
        _pool_response(pool, pool_map) for pool in await runtime_pool_service.list_pools()
    ]
    return RuntimePoolDiagnosticsEnvelope(
        diagnostics=RuntimePoolDiagnosticsResponse(
            generated_at=diagnostics["generated_at"],
            total_pools=int(diagnostics["total_pools"]),
            total_contexts=int(diagnostics["total_contexts"]),
            owned_contexts=int(diagnostics["owned_contexts"]),
            borrowed_contexts=int(diagnostics["borrowed_contexts"]),
            released_contexts=int(diagnostics["released_contexts"]),
            pools=pool_responses,
        )
    )


@router.post(
    "/runtime-pools", response_model=RuntimePoolEnvelope, status_code=status.HTTP_201_CREATED
)
async def create_runtime_pool(
    payload: RuntimePoolCreateRequest,
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
) -> RuntimePoolEnvelope:
    try:
        pool = await runtime_pool_service.create_pool(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return RuntimePoolEnvelope(
        pool=_pool_response(
            pool, _pool_diagnostics_map(await runtime_pool_service.get_pool_diagnostics())
        )
    )


@router.get("/runtime-pools/{pool_key}", response_model=RuntimePoolEnvelope)
async def get_runtime_pool(
    pool_key: str,
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
) -> RuntimePoolEnvelope:
    try:
        pool = await runtime_pool_service.get_pool(pool_key)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    diagnostics = _pool_diagnostics_map(await runtime_pool_service.get_pool_diagnostics())
    return RuntimePoolEnvelope(pool=_pool_response(pool, diagnostics))


@router.post("/runtime-pools/{pool_key}/assign", response_model=RuntimePoolAssignEnvelope)
async def assign_runtime_pool(
    pool_key: str,
    payload: RuntimePoolAssignRequest,
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> RuntimePoolAssignEnvelope:
    job = await _load_job(job_repository, payload.job_id)
    try:
        assignment = await runtime_pool_service.assign_work_context_for_job(
            job,
            preferred_pool_key=payload.preferred_pool_key or pool_key,
            required_capabilities=payload.required_capabilities,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    diagnostics = _pool_diagnostics_map(await runtime_pool_service.get_pool_diagnostics())
    pool_response = _pool_response(assignment.pool, diagnostics)
    if assignment.context is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Work context could not be created."
        )
    return RuntimePoolAssignEnvelope(
        pool=pool_response,
        context=_context_response(assignment.context, pool_key=assignment.pool.pool_key),
        fallback_used=assignment.fallback_used,
        runtime_found=assignment.runtime_found,
    )


@router.get("/work-contexts", response_model=WorkContextListEnvelope)
async def list_work_contexts(
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
    work_context_service: Annotated[WorkContextService, Depends(get_work_context_service)],
    session_id: str | None = None,
    job_id: str | None = None,
    pool_key: str | None = None,
    agent_id: str | None = None,
    context_status: str | None = None,
) -> WorkContextListEnvelope:
    pools = {pool.id: pool.pool_key for pool in await runtime_pool_service.list_pools()}
    contexts = await work_context_service.list_contexts()
    filtered = contexts
    if session_id is not None:
        filtered = [context for context in filtered if context.session_id == session_id]
    if job_id is not None:
        filtered = [context for context in filtered if context.job_id == job_id]
    if pool_key is not None:
        filtered = [
            context for context in filtered if pools.get(context.runtime_pool_id) == pool_key
        ]
    if agent_id is not None:
        filtered = [context for context in filtered if context.agent_id == agent_id]
    if context_status is not None:
        filtered = [context for context in filtered if context.context_status == context_status]
    return WorkContextListEnvelope(
        contexts=[
            _context_response(context, pool_key=pools.get(context.runtime_pool_id, "unknown"))
            for context in filtered
        ]
    )


@router.get("/work-contexts/{context_id}", response_model=WorkContextEnvelope)
async def get_work_context(
    context_id: str,
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
    work_context_service: Annotated[WorkContextService, Depends(get_work_context_service)],
) -> WorkContextEnvelope:
    context = await work_context_service.get_context(context_id)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work context not found: {context_id}",
        )
    pools = {pool.id: pool.pool_key for pool in await runtime_pool_service.list_pools()}
    return WorkContextEnvelope(
        context=_context_response(context, pool_key=pools.get(context.runtime_pool_id, "unknown"))
    )


@router.post("/work-contexts/{context_id}/recover", response_model=WorkContextEnvelope)
async def recover_work_context(
    context_id: str,
    runtime_pool_service: Annotated[RuntimePoolService, Depends(get_runtime_pool_service)],
    _payload: WorkContextRecoverRequest | None = None,
) -> WorkContextEnvelope:
    try:
        context = await runtime_pool_service.recover_work_context(context_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    pools = {pool.id: pool.pool_key for pool in await runtime_pool_service.list_pools()}
    return WorkContextEnvelope(
        context=_context_response(context, pool_key=pools.get(context.runtime_pool_id, "unknown"))
    )
