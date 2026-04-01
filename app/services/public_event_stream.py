"""Public A2A task event and subscription service."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from app.models.api.a2a_events import (
    A2APublicTaskEventResponse,
    A2APublicTaskEventType,
    A2APublicTaskSubscriptionResponse,
)
from app.models.api.a2a_public import (
    A2APublicTaskArtifactResponse,
    A2APublicTaskResponse,
)
from app.repositories.a2a_tasks import A2ATaskRecord, A2ATaskRepository
from app.repositories.public_events import PublicTaskEventRecord, PublicTaskEventRepository
from app.repositories.public_subscriptions import (
    PublicTaskSubscriptionRecord,
    PublicTaskSubscriptionRepository,
)
from app.repositories.reviews import ReviewRepository

_DELIVERY_MODE = "sse"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_json(payload: str | None) -> dict[str, Any]:
    if payload is None:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _sse(event: str, data: object, *, event_id: int | str | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, sort_keys=True)}")
    return "\n".join(lines) + "\n\n"


def _task_snapshot(task: A2APublicTaskResponse) -> dict[str, Any]:
    return task.model_dump(mode="json")


class PublicEventStreamService:
    """Coordinate the public task event log and subscription surface."""

    def __init__(
        self,
        *,
        task_repository: A2ATaskRepository,
        event_repository: PublicTaskEventRepository,
        subscription_repository: PublicTaskSubscriptionRepository,
        review_repository: ReviewRepository,
    ) -> None:
        self.task_repository = task_repository
        self.event_repository = event_repository
        self.subscription_repository = subscription_repository
        self.review_repository = review_repository

    async def create_subscription(
        self,
        *,
        task_id: str,
        since_sequence: int = 0,
    ) -> A2APublicTaskSubscriptionResponse:
        """Create a subscription cursor for a public task."""
        if since_sequence < 0:
            raise ValueError("since_sequence must be greater than or equal to 0")
        task = await self._get_task_record(task_id)
        now = _utc_now()
        subscription = PublicTaskSubscriptionRecord(
            id=f"sub_{uuid4().hex}",
            task_id=task.task_id,
            session_id=task.session_id,
            cursor_sequence=since_sequence,
            delivery_mode=_DELIVERY_MODE,
            created_at=now,
            updated_at=now,
        )
        saved = await self.subscription_repository.create(subscription)
        return self._subscription_response(saved)

    async def get_subscription(
        self,
        subscription_id: str,
    ) -> A2APublicTaskSubscriptionResponse | None:
        """Return a public task subscription by id."""
        subscription = await self.subscription_repository.get(subscription_id)
        if subscription is None:
            return None
        return self._subscription_response(subscription)

    async def list_task_events(
        self,
        *,
        task_id: str,
        since_sequence: int = 0,
    ) -> list[A2APublicTaskEventResponse]:
        """Return replayable public events for a task."""
        if since_sequence < 0:
            raise ValueError("since_sequence must be greater than or equal to 0")
        await self._get_task_record(task_id)
        events = await self.event_repository.list_since(task_id, since_sequence)
        return [self._event_response(event) for event in events]

    async def list_subscription_events(
        self,
        subscription_id: str,
        since_sequence: int | None = None,
    ) -> list[A2APublicTaskEventResponse]:
        """Return events for a subscription cursor."""
        subscription = await self._get_subscription_record(subscription_id)
        cursor = subscription.cursor_sequence if since_sequence is None else since_sequence
        return await self.list_task_events(task_id=subscription.task_id, since_sequence=cursor)

    async def stream_subscription(
        self,
        subscription_id: str,
        since_sequence: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream public task events as SSE frames."""
        events = await self.list_subscription_events(subscription_id, since_sequence)
        for event in events:
            yield _sse(event.event_type, event.model_dump(mode="json"), event_id=event.sequence)

    async def record_task_projection(
        self,
        current_task: A2APublicTaskResponse,
        *,
        previous_task: A2APublicTaskResponse | None = None,
    ) -> list[A2APublicTaskEventResponse]:
        """Append public events derived from a task projection refresh."""
        await self._get_task_record(current_task.task_id)
        event_specs = await self._build_event_specs(
            previous_task=previous_task,
            current_task=current_task,
        )
        saved_events: list[A2APublicTaskEventResponse] = []
        for event_type, change in event_specs:
            event_record = await self.event_repository.append(
                PublicTaskEventRecord(
                    id=f"pev_{uuid4().hex}",
                    task_id=current_task.task_id,
                    session_id=current_task.session_id,
                    sequence=0,
                    event_type=event_type,
                    event_payload_json=json.dumps(
                        {
                            "change": change,
                            "task": _task_snapshot(current_task),
                        },
                        sort_keys=True,
                    ),
                    created_at=_utc_now(),
                )
            )
            saved_events.append(self._event_response(event_record))
        return saved_events

    async def _build_event_specs(
        self,
        *,
        previous_task: A2APublicTaskResponse | None,
        current_task: A2APublicTaskResponse,
    ) -> list[tuple[A2APublicTaskEventType, dict[str, Any] | None]]:
        specs: list[tuple[A2APublicTaskEventType, dict[str, Any] | None]] = []
        if previous_task is None:
            specs.append(("created", {"kind": "created"}))
        if self._phase_changed(previous_task, current_task):
            specs.append(
                (
                    "phase_changed",
                    {
                        "field": "phase",
                        "before": self._phase_snapshot(previous_task),
                        "after": self._phase_snapshot(current_task),
                    },
                )
            )
        if self._status_changed(previous_task, current_task):
            specs.append(
                (
                    "status_changed",
                    {
                        "field": "status",
                        "before": self._status_snapshot(previous_task),
                        "after": current_task.status.model_dump(mode="json"),
                    },
                )
            )
        if await self._should_emit_review_requested(previous_task, current_task):
            specs.append(("review_requested", {"field": "review_requested"}))
        for artifact in self._new_artifacts(previous_task, current_task):
            specs.append(
                (
                    "artifact_attached",
                    {
                        "field": "artifact",
                        "artifact": artifact.model_dump(mode="json"),
                    },
                )
            )
        if self._completed(previous_task, current_task):
            specs.append(("completed", {"field": "completed"}))
        return specs

    def _phase_changed(
        self,
        previous_task: A2APublicTaskResponse | None,
        current_task: A2APublicTaskResponse,
    ) -> bool:
        if previous_task is None:
            return False
        return (
            previous_task.phase_id != current_task.phase_id
            or previous_task.phase_key != current_task.phase_key
            or previous_task.phase_title != current_task.phase_title
        )

    def _status_changed(
        self,
        previous_task: A2APublicTaskResponse | None,
        current_task: A2APublicTaskResponse,
    ) -> bool:
        if previous_task is None:
            return False
        return (
            previous_task.status.internal_status != current_task.status.internal_status
            or previous_task.status.state != current_task.status.state
        )

    async def _should_emit_review_requested(
        self,
        previous_task: A2APublicTaskResponse | None,
        current_task: A2APublicTaskResponse,
    ) -> bool:
        if not current_task.status.is_blocked:
            return False
        if previous_task is not None and previous_task.status.is_blocked:
            return False
        reviews = await self.review_repository.list_by_job(current_task.job_id)
        return any(review.review_status == "requested" for review in reviews)

    def _new_artifacts(
        self,
        previous_task: A2APublicTaskResponse | None,
        current_task: A2APublicTaskResponse,
    ) -> list[A2APublicTaskArtifactResponse]:
        if previous_task is None:
            return list(current_task.artifacts)
        previous_ids = {artifact.id for artifact in previous_task.artifacts}
        return [artifact for artifact in current_task.artifacts if artifact.id not in previous_ids]

    def _completed(
        self,
        previous_task: A2APublicTaskResponse | None,
        current_task: A2APublicTaskResponse,
    ) -> bool:
        if previous_task is None:
            return current_task.status.state == "completed"
        return (
            previous_task.status.state != "completed" and current_task.status.state == "completed"
        )

    def _phase_snapshot(
        self,
        task: A2APublicTaskResponse | None,
    ) -> dict[str, Any] | None:
        if task is None:
            return None
        return {
            "phase_id": task.phase_id,
            "phase_key": task.phase_key,
            "phase_title": task.phase_title,
            "phase_template_key": task.phase_template_key,
        }

    def _status_snapshot(
        self,
        task: A2APublicTaskResponse | None,
    ) -> dict[str, Any] | None:
        if task is None:
            return None
        return task.status.model_dump(mode="json")

    def _event_response(self, event: PublicTaskEventRecord) -> A2APublicTaskEventResponse:
        payload = _parse_json(event.event_payload_json)
        task_payload = payload.get("task") if isinstance(payload, dict) else None
        change = payload.get("change") if isinstance(payload, dict) else None
        return A2APublicTaskEventResponse(
            event_id=event.id,
            task_id=event.task_id,
            sequence=event.sequence,
            event_type=cast(A2APublicTaskEventType, event.event_type),
            task=A2APublicTaskResponse.model_validate(task_payload or {}),
            change=change if isinstance(change, dict) else None,
            created_at=event.created_at,
        )

    def _subscription_response(
        self,
        subscription: PublicTaskSubscriptionRecord,
    ) -> A2APublicTaskSubscriptionResponse:
        return A2APublicTaskSubscriptionResponse(
            subscription_id=subscription.id,
            task_id=subscription.task_id,
            cursor_sequence=subscription.cursor_sequence,
            delivery_mode="sse",
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

    async def _get_task_record(self, task_id: str) -> A2ATaskRecord:
        task = await self.task_repository.get(task_id)
        if task is None:
            raise LookupError(f"Public task not found: {task_id}")
        return task

    async def _get_subscription_record(
        self,
        subscription_id: str,
    ) -> PublicTaskSubscriptionRecord:
        subscription = await self.subscription_repository.get(subscription_id)
        if subscription is None:
            raise LookupError(f"Public subscription not found: {subscription_id}")
        return subscription
