"""Public A2A task routes built on top of the adapter bridge."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_a2a_public_service
from app.models.api.a2a_public import (
    A2APublicTaskCreateRequest,
    A2APublicTaskEnvelope,
    A2APublicTaskListEnvelope,
)
from app.services.a2a_public_service import A2APublicService

router = APIRouter(prefix="/api/v1/a2a", tags=["a2a"])


@router.post("/tasks", response_model=A2APublicTaskEnvelope, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: A2APublicTaskCreateRequest,
    public_service: Annotated[A2APublicService, Depends(get_a2a_public_service)],
) -> A2APublicTaskEnvelope:
    try:
        task = await public_service.create_task(payload.job_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return A2APublicTaskEnvelope(task=task)


@router.get("/tasks", response_model=A2APublicTaskListEnvelope)
async def list_tasks(
    public_service: Annotated[A2APublicService, Depends(get_a2a_public_service)],
    session_id: str | None = None,
) -> A2APublicTaskListEnvelope:
    try:
        tasks = await public_service.list_tasks(session_id=session_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return A2APublicTaskListEnvelope(tasks=tasks)


@router.get("/tasks/{task_id}", response_model=A2APublicTaskEnvelope)
async def get_task(
    task_id: str,
    public_service: Annotated[A2APublicService, Depends(get_a2a_public_service)],
) -> A2APublicTaskEnvelope:
    task = await public_service.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A2A task not found: {task_id}",
        )
    return A2APublicTaskEnvelope(task=task)
