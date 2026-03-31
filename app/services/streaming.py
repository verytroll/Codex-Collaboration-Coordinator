"""Server-sent event streaming helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from app.repositories.artifacts import ArtifactRepository
from app.repositories.jobs import JobEventRepository, JobRepository
from app.repositories.messages import MessageRepository
from app.repositories.session_events import SessionEventRepository
from app.repositories.sessions import SessionRepository


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, sort_keys=True)}\n\n"


class StreamingService:
    """Produce snapshot SSE streams for sessions and jobs."""

    def __init__(
        self,
        *,
        job_repository: JobRepository,
        job_event_repository: JobEventRepository,
        artifact_repository: ArtifactRepository,
        session_repository: SessionRepository,
        session_event_repository: SessionEventRepository,
        message_repository: MessageRepository,
    ) -> None:
        self.job_repository = job_repository
        self.job_event_repository = job_event_repository
        self.artifact_repository = artifact_repository
        self.session_repository = session_repository
        self.session_event_repository = session_event_repository
        self.message_repository = message_repository

    async def stream_job(self, job_id: str) -> AsyncIterator[str]:
        """Stream a snapshot of a job timeline."""
        job = await self.job_repository.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        yield _sse("job", asdict(job))

        for event in await self.job_event_repository.list_by_job(job_id):
            yield _sse(
                "job_event",
                {
                    "id": event.id,
                    "job_id": event.job_id,
                    "session_id": event.session_id,
                    "event_type": event.event_type,
                    "payload": event.event_payload_json,
                    "created_at": event.created_at,
                },
            )

        for artifact in await self.artifact_repository.list_by_job(job_id):
            yield _sse(
                "artifact",
                {
                    "id": artifact.id,
                    "artifact_type": artifact.artifact_type,
                    "title": artifact.title,
                },
            )

    async def stream_session(self, session_id: str) -> AsyncIterator[str]:
        """Stream a snapshot of a session timeline."""
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        yield _sse("session", asdict(session))

        for event in await self.session_event_repository.list_by_session(session_id):
            yield _sse(
                "session_event",
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "actor_type": event.actor_type,
                    "actor_id": event.actor_id,
                    "payload": event.event_payload_json,
                    "created_at": event.created_at,
                },
            )

        for message in await self.message_repository.list_by_session(session_id):
            yield _sse(
                "message",
                {
                    "id": message.id,
                    "message_type": message.message_type,
                    "sender_type": message.sender_type,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "created_at": message.created_at,
                },
            )
