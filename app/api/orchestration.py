"""Orchestration API routes."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_orchestration_engine_service,
    get_phase_gate_service,
    get_session_repository,
)
from app.models.api.orchestration import (
    OrchestrationGateEnvelope,
    OrchestrationGateRequest,
    OrchestrationRunEnvelope,
    OrchestrationRunListEnvelope,
    OrchestrationRunResponse,
)
from app.repositories.sessions import SessionRepository
from app.services.orchestration_engine import OrchestrationEngineService
from app.services.phase_gate_service import PhaseGateService

router = APIRouter(prefix="/api/v1", tags=["orchestration"])


def _run_response(run) -> OrchestrationRunResponse:
    return OrchestrationRunResponse(
        id=run.id,
        session_id=run.session_id,
        status=cast(str, run.status),
        current_phase_id=run.current_phase_id,
        current_phase_key=run.current_phase_key,
        pending_phase_key=run.pending_phase_key,
        failure_phase_key=run.failure_phase_key,
        gate_type=cast(str | None, run.gate_type),
        gate_status=cast(str, run.gate_status),
        source_job_id=run.source_job_id,
        handoff_job_id=run.handoff_job_id,
        review_id=run.review_id,
        approval_id=run.approval_id,
        transition_artifact_id=run.transition_artifact_id,
        decision_artifact_id=run.decision_artifact_id,
        revision_job_id=run.revision_job_id,
        requested_by_agent_id=run.requested_by_agent_id,
        transition_reason=run.transition_reason,
        started_at=run.started_at,
        decided_at=run.decided_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


async def _ensure_session_exists(
    session_repository: SessionRepository,
    session_id: str,
) -> None:
    if await session_repository.get(session_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )


@router.get("/orchestration/runs", response_model=OrchestrationRunListEnvelope)
async def list_orchestration_runs(
    orchestration_engine_service: Annotated[
        OrchestrationEngineService,
        Depends(get_orchestration_engine_service),
    ],
) -> OrchestrationRunListEnvelope:
    return OrchestrationRunListEnvelope(
        runs=[_run_response(run) for run in await orchestration_engine_service.list_runs()]
    )


@router.get("/orchestration/sessions/{session_id}", response_model=OrchestrationRunEnvelope)
async def get_orchestration_run(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    orchestration_engine_service: Annotated[
        OrchestrationEngineService,
        Depends(get_orchestration_engine_service),
    ],
) -> OrchestrationRunEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    run = await orchestration_engine_service.get_run_by_session(session_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orchestration run not found for session: {session_id}",
        )
    return OrchestrationRunEnvelope(run=_run_response(run))


@router.post(
    "/orchestration/sessions/{session_id}/start",
    response_model=OrchestrationRunEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def start_orchestration_run(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_gate_service: Annotated[PhaseGateService, Depends(get_phase_gate_service)],
) -> OrchestrationRunEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    result = await phase_gate_service.start_run(session_id)
    return OrchestrationRunEnvelope(run=_run_response(result.run))


@router.post(
    "/orchestration/sessions/{session_id}/gate",
    response_model=OrchestrationGateEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def request_orchestration_gate(
    session_id: str,
    payload: OrchestrationGateRequest,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    phase_gate_service: Annotated[PhaseGateService, Depends(get_phase_gate_service)],
) -> OrchestrationGateEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    try:
        if payload.gate_type == "review_required":
            result = await phase_gate_service.request_review_gate(
                session_id=session_id,
                source_job_id=payload.source_job_id,
                reviewer_agent_id=payload.reviewer_agent_id,
                requested_by_agent_id=payload.requested_by_agent_id,
                success_phase_key=payload.success_phase_key,
                failure_phase_key=payload.failure_phase_key,
                notes=payload.notes,
            )
        elif payload.gate_type == "approval_required":
            result = await phase_gate_service.request_approval_gate(
                session_id=session_id,
                source_job_id=payload.source_job_id,
                approver_agent_id=payload.approver_agent_id,
                requested_by_agent_id=payload.requested_by_agent_id,
                success_phase_key=payload.success_phase_key,
                failure_phase_key=payload.failure_phase_key,
                notes=payload.notes,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="revise_on_reject can only be produced by a gate decision",
            )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OrchestrationGateEnvelope(
        run=_run_response(result.run),
        source_job_id=result.source_job.id,
        handoff_job_id=result.handoff_job.id if result.handoff_job is not None else None,
        review_id=result.review.id if result.review is not None else None,
        approval_id=result.approval_id,
        transition_artifact_id=result.transition_artifact.id,
    )
