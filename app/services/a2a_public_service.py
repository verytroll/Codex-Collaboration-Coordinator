"""Public A2A task projection service."""

from __future__ import annotations

import json
from typing import Any, cast

from app.models.api.a2a_public import (
    A2APublicTaskArtifactResponse,
    A2APublicTaskErrorResponse,
    A2APublicTaskResponse,
    A2APublicTaskStatusResponse,
)
from app.repositories.a2a_tasks import A2ATaskRecord, A2ATaskRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.services.a2a_adapter import A2AAdapterService, A2ATaskProjection
from app.services.authz_service import ActorIdentity
from app.services.outbound_webhooks import OutboundWebhookService
from app.services.public_event_stream import PublicEventStreamService
from app.services.session_events import record_session_event

_PUBLIC_STATUS_BY_INTERNAL_STATUS: dict[str, str] = {
    "queued": "queued",
    "running": "in_progress",
    "blocked": "blocked",
    "input_required": "blocked",
    "auth_required": "blocked",
    "paused_by_loop_guard": "blocked",
    "completed": "completed",
    "failed": "failed",
    "canceled": "canceled",
}

_TERMINAL_STATES = {"completed", "failed", "canceled"}
_BLOCKED_STATES = {"blocked"}


def _parse_json(payload: str | None) -> dict[str, object]:
    if payload is None:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _public_state(internal_status: str) -> str:
    return _PUBLIC_STATUS_BY_INTERNAL_STATUS.get(internal_status, "failed")


def _status_payload(
    *,
    internal_status: str,
    started_at: str | None,
    completed_at: str | None,
    updated_at: str,
) -> A2APublicTaskStatusResponse:
    public_state = _public_state(internal_status)
    return A2APublicTaskStatusResponse(
        state=cast(Any, public_state),
        internal_status=internal_status,
        is_terminal=public_state in _TERMINAL_STATES,
        is_blocked=public_state in _BLOCKED_STATES,
        started_at=started_at,
        completed_at=completed_at,
        updated_at=updated_at,
    )


def _artifact_payload(
    artifact_payload: dict[str, object],
    *,
    primary_artifact_id: str | None,
) -> A2APublicTaskArtifactResponse:
    artifact_id = str(artifact_payload.get("id", ""))
    return A2APublicTaskArtifactResponse(
        id=artifact_id,
        artifact_type=str(artifact_payload.get("artifact_type", "")),
        title=str(artifact_payload.get("title", "")),
        file_name=(
            artifact_payload.get("file_name")
            if isinstance(artifact_payload.get("file_name"), str)
            else None
        ),
        mime_type=(
            artifact_payload.get("mime_type")
            if isinstance(artifact_payload.get("mime_type"), str)
            else None
        ),
        size_bytes=(
            artifact_payload.get("size_bytes")
            if isinstance(artifact_payload.get("size_bytes"), int)
            else None
        ),
        checksum_sha256=(
            artifact_payload.get("checksum_sha256")
            if isinstance(artifact_payload.get("checksum_sha256"), str)
            else None
        ),
        channel_key=str(artifact_payload.get("channel_key", "general")),
        is_primary=artifact_id == primary_artifact_id,
    )


def _error_payload(
    *,
    internal_status: str,
    error_code: str | None,
    error_message: str | None,
    job_payload: dict[str, object],
) -> A2APublicTaskErrorResponse | None:
    if (
        error_code is None
        and error_message is None
        and internal_status
        not in {
            "failed",
            "canceled",
        }
    ):
        return None
    if error_code is not None:
        code = error_code
    elif internal_status == "canceled":
        code = "job_canceled"
    elif internal_status == "failed":
        code = "job_failed"
    else:
        code = "task_error"

    if error_message is not None:
        message = error_message
    elif internal_status == "canceled":
        message = "Job canceled"
    elif internal_status == "failed":
        message = "Job failed"
    else:
        message = "Task error"
    details: dict[str, Any] = {
        "job_id": job_payload.get("job_id"),
        "session_id": job_payload.get("session_id"),
        "phase_key": job_payload.get("phase_key"),
        "assigned_agent_id": job_payload.get("assigned_agent_id"),
    }
    return A2APublicTaskErrorResponse(code=code, message=message, details=details)


class A2APublicService:
    """Expose the adapter bridge through the public task contract."""

    def __init__(
        self,
        *,
        adapter_service: A2AAdapterService,
        task_repository: A2ATaskRepository,
        session_repository: SessionRepository,
        session_event_repository: SessionEventRepository | None = None,
        event_stream_service: PublicEventStreamService | None = None,
        outbound_webhook_service: OutboundWebhookService | None = None,
    ) -> None:
        self.adapter_service = adapter_service
        self.task_repository = task_repository
        self.session_repository = session_repository
        self.session_event_repository = session_event_repository
        self.event_stream_service = event_stream_service
        self.outbound_webhook_service = outbound_webhook_service

    async def create_task(
        self,
        job_id: str,
        *,
        actor_identity: ActorIdentity | None = None,
    ) -> A2APublicTaskResponse:
        """Create or refresh the public task projection for a job."""
        previous_projection = await self.adapter_service.get_task_by_job(job_id)
        projection = await self.adapter_service.project_job(job_id)
        task = self._response_from_projection(projection)
        if self.session_event_repository is not None:
            await record_session_event(
                self.session_event_repository,
                session_id=task.session_id,
                event_type="public.task.projected",
                actor_type=(
                    actor_identity.actor_role
                    if actor_identity is not None
                    else "integration_client"
                ),
                actor_id=actor_identity.actor_id if actor_identity is not None else None,
                payload={
                    "job_id": task.job_id,
                    "task_id": task.task_id,
                    "actor": actor_identity.as_payload() if actor_identity is not None else None,
                },
            )
        if self.event_stream_service is not None:
            previous_task = (
                self._response_from_projection(previous_projection)
                if previous_projection is not None
                else None
            )
            saved_events = await self.event_stream_service.record_task_projection(
                task,
                previous_task=previous_task,
            )
            if self.outbound_webhook_service is not None and saved_events:
                await self.outbound_webhook_service.enqueue_events(
                    task_id=task.task_id,
                    session_id=task.session_id,
                    events=saved_events,
                )
                await self.outbound_webhook_service.dispatch_task_deliveries(task.task_id)
        return task

    async def get_task(self, task_id: str) -> A2APublicTaskResponse | None:
        """Return a public task projection by task id."""
        projection = await self.adapter_service.get_task(task_id)
        if projection is None:
            return None
        return self._response_from_projection(projection)

    async def list_tasks(self, session_id: str | None = None) -> list[A2APublicTaskResponse]:
        """Return public task projections, optionally scoped to a session."""
        if session_id is not None:
            await self._ensure_session(session_id)
            records = await self.task_repository.list_by_session(session_id)
        else:
            records = await self.task_repository.list()
        return [self._response_from_record(record) for record in records]

    def _response_from_projection(self, projection: A2ATaskProjection) -> A2APublicTaskResponse:
        return self._response_from_record(projection.record, projection.payload)

    def _response_from_record(
        self,
        record: A2ATaskRecord,
        payload: dict[str, object] | None = None,
    ) -> A2APublicTaskResponse:
        resolved_payload = payload if payload is not None else _parse_json(record.task_payload_json)
        artifacts_payload = resolved_payload.get("artifacts")
        artifacts = []
        if isinstance(artifacts_payload, list):
            artifacts = [
                _artifact_payload(item, primary_artifact_id=record.primary_artifact_id)
                for item in artifacts_payload
                if isinstance(item, dict)
            ]
        status = _status_payload(
            internal_status=record.task_status,
            started_at=resolved_payload.get("started_at")
            if isinstance(resolved_payload.get("started_at"), str)
            else None,
            completed_at=resolved_payload.get("completed_at")
            if isinstance(resolved_payload.get("completed_at"), str)
            else None,
            updated_at=str(resolved_payload.get("updated_at", record.updated_at)),
        )
        error = _error_payload(
            internal_status=record.task_status,
            error_code=resolved_payload.get("error_code")
            if isinstance(resolved_payload.get("error_code"), str)
            else None,
            error_message=resolved_payload.get("error_message")
            if isinstance(resolved_payload.get("error_message"), str)
            else None,
            job_payload=resolved_payload,
        )
        metadata = resolved_payload.get("metadata")
        return A2APublicTaskResponse(
            task_id=str(resolved_payload.get("task_id", record.task_id)),
            context_id=str(resolved_payload.get("context_id", record.context_id)),
            session_id=str(resolved_payload.get("session_id", record.session_id)),
            job_id=str(resolved_payload.get("job_id", record.job_id)),
            phase_id=(
                resolved_payload.get("phase_id")
                if isinstance(resolved_payload.get("phase_id"), str)
                else record.phase_id
            ),
            phase_key=(
                resolved_payload.get("phase_key")
                if isinstance(resolved_payload.get("phase_key"), str)
                else None
            ),
            phase_title=(
                resolved_payload.get("phase_title")
                if isinstance(resolved_payload.get("phase_title"), str)
                else None
            ),
            phase_template_key=(
                resolved_payload.get("phase_template_key")
                if isinstance(resolved_payload.get("phase_template_key"), str)
                else record.relay_template_key
            ),
            relay_template_key=(
                resolved_payload.get("relay_template_key")
                if isinstance(resolved_payload.get("relay_template_key"), str)
                else record.relay_template_key
            ),
            assigned_agent_id=str(resolved_payload.get("assigned_agent_id", "")),
            title=str(resolved_payload.get("title", "")),
            summary=(
                resolved_payload.get("summary")
                if isinstance(resolved_payload.get("summary"), str)
                else None
            ),
            status=status,
            artifacts=artifacts,
            error=error,
            metadata=metadata if isinstance(metadata, dict) else None,
            created_at=str(resolved_payload.get("created_at", record.created_at)),
            updated_at=str(resolved_payload.get("updated_at", record.updated_at)),
        )

    async def _ensure_session(self, session_id: str) -> None:
        if await self.session_repository.get(session_id) is None:
            raise LookupError(f"Session not found: {session_id}")
