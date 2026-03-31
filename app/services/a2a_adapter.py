"""Experimental A2A adapter bridge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.a2a_tasks import A2ATaskRecord, A2ATaskRepository
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobRecord, JobRepository
from app.repositories.phases import PhaseRecord
from app.repositories.sessions import SessionRecord, SessionRepository
from app.services.phase_service import PhaseService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _map_job_status(status: str) -> str:
    mapping = {
        "queued": "queued",
        "running": "in_progress",
        "input_required": "blocked",
        "auth_required": "blocked",
        "paused_by_loop_guard": "blocked",
        "completed": "completed",
        "failed": "failed",
        "canceled": "canceled",
    }
    return mapping.get(status, status)


def _artifact_summary(artifact: ArtifactRecord) -> dict[str, object]:
    return {
        "id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "title": artifact.title,
        "file_name": artifact.file_name,
        "mime_type": artifact.mime_type,
        "size_bytes": artifact.size_bytes,
        "checksum_sha256": artifact.checksum_sha256,
        "channel_key": artifact.channel_key,
    }


@dataclass(frozen=True, slots=True)
class A2ATaskProjection:
    """Projected A2A task payload."""

    record: A2ATaskRecord
    payload: dict[str, object]


class A2AAdapterService:
    """Project internal jobs into a simple A2A task mapping."""

    def __init__(
        self,
        *,
        task_repository: A2ATaskRepository,
        job_repository: JobRepository,
        artifact_repository: ArtifactRepository,
        session_repository: SessionRepository,
        phase_service: PhaseService,
    ) -> None:
        self.task_repository = task_repository
        self.job_repository = job_repository
        self.artifact_repository = artifact_repository
        self.session_repository = session_repository
        self.phase_service = phase_service

    async def project_job(self, job_id: str) -> A2ATaskProjection:
        """Create or refresh an A2A task mapping for a job."""
        job = await self._get_job(job_id)
        session = await self._get_session(job.session_id)
        phase = await self.phase_service.get_active_phase(session.id)
        artifacts = await self.artifact_repository.list_by_job(job.id)
        now = _utc_now()
        existing = await self.task_repository.get_by_job(job.id)
        task_id = existing.task_id if existing is not None else f"tsk_{uuid4().hex}"
        record_id = existing.id if existing is not None else f"a2a_{uuid4().hex}"
        payload = self._build_payload(
            job=job,
            session=session,
            phase=phase,
            artifacts=artifacts,
            task_id=task_id,
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        record = A2ATaskRecord(
            id=record_id,
            session_id=session.id,
            job_id=job.id,
            phase_id=phase.id if phase is not None else None,
            task_id=task_id,
            context_id=session.id,
            task_status=str(payload["status"]),
            relay_template_key=phase.relay_template_key if phase is not None else None,
            primary_artifact_id=payload["primary_artifact_id"],
            task_payload_json=json.dumps(payload, sort_keys=True),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        saved = await (self.task_repository.update(record) if existing is not None else self.task_repository.create(record))
        return A2ATaskProjection(record=saved, payload=payload)

    async def get_task(self, task_id: str) -> A2ATaskProjection | None:
        """Return a projected task by task id."""
        record = await self.task_repository.get(task_id)
        if record is None:
            return None
        return A2ATaskProjection(record=record, payload=self._parse_payload(record))

    async def list_tasks(self, session_id: str) -> list[A2ATaskProjection]:
        """Return projected tasks for a session."""
        records = await self.task_repository.list_by_session(session_id)
        return [A2ATaskProjection(record=record, payload=self._parse_payload(record)) for record in records]

    async def get_task_by_job(self, job_id: str) -> A2ATaskProjection | None:
        """Return a projected task by job id."""
        record = await self.task_repository.get_by_job(job_id)
        if record is None:
            return None
        return A2ATaskProjection(record=record, payload=self._parse_payload(record))

    def _build_payload(
        self,
        *,
        job: JobRecord,
        session: SessionRecord,
        phase: PhaseRecord | None,
        artifacts: list[ArtifactRecord],
        task_id: str,
        created_at: str,
        updated_at: str,
    ) -> dict[str, object]:
        primary_artifact = artifacts[-1] if artifacts else None
        task_artifacts = [_artifact_summary(artifact) for artifact in artifacts]
        summary = job.result_summary or job.instructions or job.title
        payload: dict[str, object] = {
            "task_id": task_id,
            "context_id": session.id,
            "session_id": session.id,
            "job_id": job.id,
            "phase_id": phase.id if phase is not None else None,
            "phase_key": phase.phase_key if phase is not None else None,
            "phase_title": phase.title if phase is not None else None,
            "phase_template_key": phase.relay_template_key if phase is not None else None,
            "status": _map_job_status(job.status),
            "title": job.title,
            "summary": summary,
            "assigned_agent_id": job.assigned_agent_id,
            "relay_template_key": phase.relay_template_key if phase is not None else None,
            "primary_artifact_id": primary_artifact.id if primary_artifact is not None else None,
            "artifacts": task_artifacts,
            "metadata": {
                "channel_key": job.channel_key,
                "priority": job.priority,
                "source_message_id": job.source_message_id,
                "parent_job_id": job.parent_job_id,
                "runtime_id": job.runtime_id,
                "artifact_ids": [artifact.id for artifact in artifacts],
            },
            "created_at": created_at,
            "updated_at": updated_at,
        }
        return payload

    def _parse_payload(self, record: A2ATaskRecord) -> dict[str, object]:
        try:
            payload = json.loads(record.task_payload_json)
        except json.JSONDecodeError:
            payload = {}
        return payload if isinstance(payload, dict) else {}

    async def _get_job(self, job_id: str) -> JobRecord:
        job = await self.job_repository.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        return job

    async def _get_session(self, session_id: str) -> SessionRecord:
        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        return session
