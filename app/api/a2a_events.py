"""Public A2A task event and subscription routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_a2a_public_event_stream_service
from app.models.api.a2a_events import (
    A2APublicTaskEventListEnvelope,
    A2APublicTaskSubscriptionCreateRequest,
    A2APublicTaskSubscriptionEnvelope,
)
from app.services.public_event_stream import PublicEventStreamService

router = APIRouter(prefix="/api/v1/a2a", tags=["a2a"])


async def _event_stream(events) -> AsyncIterator[str]:
    for event in events:
        yield (
            f"id: {event.sequence}\n"
            f"event: {event.event_type}\n"
            f"data: {event.model_dump_json()}\n\n"
        )


@router.post(
    "/tasks/{task_id}/subscriptions",
    response_model=A2APublicTaskSubscriptionEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    task_id: str,
    payload: A2APublicTaskSubscriptionCreateRequest,
    public_event_service: Annotated[
        PublicEventStreamService,
        Depends(get_a2a_public_event_stream_service),
    ],
) -> A2APublicTaskSubscriptionEnvelope:
    try:
        subscription = await public_event_service.create_subscription(
            task_id=task_id,
            since_sequence=payload.since_sequence,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return A2APublicTaskSubscriptionEnvelope(subscription=subscription)


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=A2APublicTaskSubscriptionEnvelope,
)
async def get_subscription(
    subscription_id: str,
    public_event_service: Annotated[
        PublicEventStreamService,
        Depends(get_a2a_public_event_stream_service),
    ],
) -> A2APublicTaskSubscriptionEnvelope:
    subscription = await public_event_service.get_subscription(subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Public subscription not found: {subscription_id}",
        )
    return A2APublicTaskSubscriptionEnvelope(subscription=subscription)


@router.get(
    "/tasks/{task_id}/events",
    response_model=A2APublicTaskEventListEnvelope,
)
async def list_task_events(
    task_id: str,
    public_event_service: Annotated[
        PublicEventStreamService,
        Depends(get_a2a_public_event_stream_service),
    ],
    since_sequence: int = Query(default=0, ge=0),
) -> A2APublicTaskEventListEnvelope:
    try:
        events = await public_event_service.list_task_events(
            task_id=task_id,
            since_sequence=since_sequence,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return A2APublicTaskEventListEnvelope(
        task_id=task_id,
        since_sequence=since_sequence,
        events=events,
    )


@router.get("/subscriptions/{subscription_id}/events")
async def stream_subscription_events(
    subscription_id: str,
    public_event_service: Annotated[
        PublicEventStreamService,
        Depends(get_a2a_public_event_stream_service),
    ],
    since_sequence: int | None = Query(default=None, ge=0),
) -> StreamingResponse:
    subscription = await public_event_service.get_subscription(subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Public subscription not found: {subscription_id}",
        )
    try:
        events = await public_event_service.list_subscription_events(
            subscription_id,
            since_sequence,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return StreamingResponse(_event_stream(events), media_type="text/event-stream")
