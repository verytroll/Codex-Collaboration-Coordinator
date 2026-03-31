"""Experimental A2A adapter bridge routes."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_a2a_adapter_service,
    get_session_repository,
)
from app.models.api.a2a_adapter import (
    A2AAdapterArtifactResponse,
    A2ATaskEnvelope,
    A2ATaskListEnvelope,
    A2ATaskResponse,
)
from app.repositories.sessions import SessionRepository
from app.services.a2a_adapter import A2AAdapterService, A2ATaskProjection

router = APIRouter(prefix="/api/v1/a2a", tags=["a2a"])


def _parse_json(payload: Any) -> dict[str, object] | None:
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _artifact_response(payload: dict[str, object]) -> A2AAdapterArtifactResponse:
    return A2AAdapterArtifactResponse(
        id=str(payload.get("id", "")),
        artifact_type=str(payload.get("artifact_type", "")),
        title=str(payload.get("title", "")),
        file_name=payload.get("file_name") if isinstance(payload.get("file_name"), str) else None,
        mime_type=payload.get("mime_type") if isinstance(payload.get("mime_type"), str) else None,
        size_bytes=payload.get("size_bytes") if isinstance(payload.get("size_bytes"), int) else None,
        checksum_sha256=(
            payload.get("checksum_sha256")
            if isinstance(payload.get("checksum_sha256"), str)
            else None
        ),
        channel_key=str(payload.get("channel_key", "general")),
    )


def _task_response(projection: A2ATaskProjection) -> A2ATaskResponse:
    payload = projection.payload
    artifacts_payload = payload.get("artifacts")
    artifacts = []
    if isinstance(artifacts_payload, list):
        artifacts = [
            _artifact_response(item)
            for item in artifacts_payload
            if isinstance(item, dict)
        ]
    metadata = _parse_json(payload.get("metadata"))
    return A2ATaskResponse(
        task_id=str(payload.get("task_id", projection.record.task_id)),
        session_id=str(payload.get("session_id", projection.record.session_id)),
        job_id=str(payload.get("job_id", projection.record.job_id)),
        phase_id=payload.get("phase_id") if isinstance(payload.get("phase_id"), str) else None,
        phase_key=payload.get("phase_key") if isinstance(payload.get("phase_key"), str) else None,
        phase_title=(
            payload.get("phase_title") if isinstance(payload.get("phase_title"), str) else None
        ),
        context_id=str(payload.get("context_id", projection.record.context_id)),
        status=str(payload.get("status", projection.record.task_status)),
        title=str(payload.get("title", "")),
        summary=payload.get("summary") if isinstance(payload.get("summary"), str) else None,
        relay_template_key=(
            payload.get("relay_template_key")
            if isinstance(payload.get("relay_template_key"), str)
            else projection.record.relay_template_key
        ),
        assigned_agent_id=str(payload.get("assigned_agent_id", "")),
        artifacts=artifacts,
        metadata=metadata,
        created_at=str(payload.get("created_at", projection.record.created_at)),
        updated_at=str(payload.get("updated_at", projection.record.updated_at)),
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


@router.post("/jobs/{job_id}/project", response_model=A2ATaskEnvelope, status_code=status.HTTP_201_CREATED)
async def project_job(
    job_id: str,
    adapter_service: Annotated[A2AAdapterService, Depends(get_a2a_adapter_service)],
) -> A2ATaskEnvelope:
    try:
        projection = await adapter_service.project_job(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return A2ATaskEnvelope(task=_task_response(projection))


@router.get("/tasks/{task_id}", response_model=A2ATaskEnvelope)
async def get_task(
    task_id: str,
    adapter_service: Annotated[A2AAdapterService, Depends(get_a2a_adapter_service)],
) -> A2ATaskEnvelope:
    projection = await adapter_service.get_task(task_id)
    if projection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A2A task not found: {task_id}",
        )
    return A2ATaskEnvelope(task=_task_response(projection))


@router.get("/sessions/{session_id}/tasks", response_model=A2ATaskListEnvelope)
async def list_session_tasks(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    adapter_service: Annotated[A2AAdapterService, Depends(get_a2a_adapter_service)],
) -> A2ATaskListEnvelope:
    await _ensure_session_exists(session_repository, session_id)
    return A2ATaskListEnvelope(
        tasks=[_task_response(projection) for projection in await adapter_service.list_tasks(session_id)]
    )
