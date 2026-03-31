"""Job API routes."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_approval_manager,
    get_approval_repository,
    get_artifact_repository,
    get_job_event_repository,
    get_job_repository,
    get_relay_engine,
    get_session_repository,
    get_streaming_service,
)
from app.models.api.jobs import (
    ApprovalRequestResponse,
    ArtifactListEnvelope,
    ArtifactResponse,
    JobControlRequest,
    JobDetailResponse,
    JobEnvelope,
    JobEventListEnvelope,
    JobEventResponse,
    JobInputRequest,
    JobResponse,
)
from app.repositories.approvals import ApprovalRepository, ApprovalRequestRecord
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord, JobRepository
from app.repositories.sessions import SessionRepository
from app.services.approval_manager import ApprovalManager
from app.services.relay_engine import RelayEngine
from app.services.streaming import StreamingService

router = APIRouter(prefix="/api/v1", tags=["jobs"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_json(payload: str | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload}
    return data if isinstance(data, dict) else {"value": data}


def _job_response(job: JobRecord) -> JobResponse:
    return JobResponse(
        id=job.id,
        session_id=job.session_id,
        assigned_agent_id=job.assigned_agent_id,
        runtime_id=job.runtime_id,
        source_message_id=job.source_message_id,
        parent_job_id=job.parent_job_id,
        title=job.title,
        instructions=job.instructions,
        status=cast(Any, job.status),
        hop_count=job.hop_count,
        priority=cast(Any, job.priority),
        codex_runtime_id=job.codex_runtime_id,
        codex_thread_id=job.codex_thread_id,
        active_turn_id=job.active_turn_id,
        last_known_turn_status=job.last_known_turn_status,
        result_summary=job.result_summary,
        error_code=job.error_code,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _event_response(event: JobEventRecord) -> JobEventResponse:
    return JobEventResponse(
        id=event.id,
        job_id=event.job_id,
        session_id=event.session_id,
        event_type=event.event_type,
        event_payload=_parse_json(event.event_payload_json),
        created_at=event.created_at,
    )


def _artifact_response(artifact: ArtifactRecord) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact.id,
        job_id=artifact.job_id,
        session_id=artifact.session_id,
        source_message_id=artifact.source_message_id,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        content_text=artifact.content_text,
        file_path=artifact.file_path,
        file_name=artifact.file_name,
        mime_type=artifact.mime_type,
        size_bytes=artifact.size_bytes,
        checksum_sha256=artifact.checksum_sha256,
        metadata=_parse_json(artifact.metadata_json),
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


def _approval_response(approval: ApprovalRequestRecord) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=approval.id,
        job_id=approval.job_id,
        agent_id=approval.agent_id,
        approval_type=approval.approval_type,
        status=approval.status,
        request_payload=_parse_json(approval.request_payload_json) or {},
        decision_payload=_parse_json(approval.decision_payload_json),
        requested_at=approval.requested_at,
        resolved_at=approval.resolved_at,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
    )


async def _ensure_job(
    job_repository: JobRepository,
    job_id: str,
) -> JobRecord:
    job = await job_repository.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )
    return job


async def _load_job_detail(
    job_id: str,
    job_repository: JobRepository,
    job_event_repository: JobEventRepository,
    artifact_repository: ArtifactRepository,
    approval_repository: ApprovalRepository,
) -> JobDetailResponse:
    job = await _ensure_job(job_repository, job_id)
    return JobDetailResponse(
        job=_job_response(job),
        events=[_event_response(event) for event in await job_event_repository.list_by_job(job_id)],
        artifacts=[
            _artifact_response(artifact)
            for artifact in await artifact_repository.list_by_job(job_id)
        ],
        approvals=[
            _approval_response(approval)
            for approval in await approval_repository.list_by_job(job_id)
        ],
    )


@router.get("/jobs/{job_id}", response_model=JobEnvelope)
async def get_job(
    job_id: str,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
) -> JobEnvelope:
    return JobEnvelope(
        job=await _load_job_detail(
            job_id,
            job_repository,
            job_event_repository,
            artifact_repository,
            approval_repository,
        )
    )


@router.get("/jobs/{job_id}/events", response_model=JobEventListEnvelope)
async def list_job_events(
    job_id: str,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
) -> JobEventListEnvelope:
    await _ensure_job(job_repository, job_id)
    return JobEventListEnvelope(
        events=[_event_response(event) for event in await job_event_repository.list_by_job(job_id)]
    )


@router.get("/jobs/{job_id}/artifacts", response_model=ArtifactListEnvelope)
async def list_job_artifacts(
    job_id: str,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
) -> ArtifactListEnvelope:
    await _ensure_job(job_repository, job_id)
    return ArtifactListEnvelope(
        artifacts=[
            _artifact_response(artifact)
            for artifact in await artifact_repository.list_by_job(job_id)
        ]
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobEnvelope)
async def cancel_job(
    job_id: str,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    relay_engine: Annotated[RelayEngine, Depends(get_relay_engine)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    payload: JobControlRequest | None = None,
) -> JobEnvelope:
    await _ensure_job(job_repository, job_id)
    try:
        await relay_engine.interrupt_job(job_id, reason=payload.reason if payload else None)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return JobEnvelope(
        job=await _load_job_detail(
            job_id,
            job_repository,
            job_event_repository,
            artifact_repository,
            approval_repository,
        )
    )


@router.post("/jobs/{job_id}/resume", response_model=JobEnvelope)
async def resume_job(
    job_id: str,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    relay_engine: Annotated[RelayEngine, Depends(get_relay_engine)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
    payload: JobControlRequest | None = None,
) -> JobEnvelope:
    job = await _ensure_job(job_repository, job_id)
    resumed_job = replace(
        job,
        status="queued",
        last_known_turn_status="resumed",
        completed_at=None,
        updated_at=_utc_now(),
    )
    await job_repository.update(resumed_job)
    try:
        await relay_engine.execute_job(
            job_id,
            relay_reason=(payload.reason if payload and payload.reason else "manual_relay"),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return JobEnvelope(
        job=await _load_job_detail(
            job_id,
            job_repository,
            job_event_repository,
            artifact_repository,
            approval_repository,
        )
    )


@router.post("/jobs/{job_id}/input", response_model=JobEnvelope)
async def provide_job_input(
    job_id: str,
    payload: JobInputRequest,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    approval_manager: Annotated[ApprovalManager, Depends(get_approval_manager)],
    relay_engine: Annotated[RelayEngine, Depends(get_relay_engine)],
    job_event_repository: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    approval_repository: Annotated[ApprovalRepository, Depends(get_approval_repository)],
) -> JobEnvelope:
    job = await _ensure_job(job_repository, job_id)
    if payload.approval_id is not None:
        try:
            await approval_manager.accept(
                payload.approval_id,
                decision_payload={"input_text": payload.input_text},
            )
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        try:
            await relay_engine.execute_job(job_id, relay_reason="manual_relay")
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    else:
        updated_job = replace(
            job,
            status="queued" if job.status in {"input_required", "auth_required"} else job.status,
            last_known_turn_status="input_received",
            instructions=(
                f"{job.instructions or ''}\n\nInput: {payload.input_text}".strip()
                if payload.input_text
                else job.instructions
            ),
            updated_at=_utc_now(),
        )
        await job_repository.update(updated_job)
        await job_event_repository.create(
            JobEventRecord(
                id=f"jbe_{uuid4().hex}",
                job_id=job.id,
                session_id=job.session_id,
                event_type="job.input_received",
                event_payload_json=json.dumps({"input_text": payload.input_text}, sort_keys=True),
                created_at=_utc_now(),
            )
        )
        if job.status in {"input_required", "auth_required"}:
            try:
                await relay_engine.execute_job(job_id, relay_reason="manual_relay")
            except LookupError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return JobEnvelope(
        job=await _load_job_detail(
            job_id,
            job_repository,
            job_event_repository,
            artifact_repository,
            approval_repository,
        )
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job(
    job_id: str,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    streaming_service: Annotated[StreamingService, Depends(get_streaming_service)],
) -> StreamingResponse:
    await _ensure_job(job_repository, job_id)
    return StreamingResponse(
        streaming_service.stream_job(job_id),
        media_type="text/event-stream",
    )


@router.get("/sessions/{session_id}/stream")
async def stream_session(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    streaming_service: Annotated[StreamingService, Depends(get_streaming_service)],
) -> StreamingResponse:
    session = await session_repository.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return StreamingResponse(
        streaming_service.stream_session(session_id),
        media_type="text/event-stream",
    )
