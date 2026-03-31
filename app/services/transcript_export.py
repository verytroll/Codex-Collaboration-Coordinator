"""Transcript export helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.artifacts import ArtifactRepository
from app.repositories.jobs import JobRepository
from app.repositories.messages import MessageMentionRepository, MessageRepository
from app.repositories.session_events import SessionEventRecord, SessionEventRepository
from app.repositories.sessions import SessionRepository
from app.repositories.transcript_exports import (
    TranscriptExportRecord,
    TranscriptExportRepository,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_mentions_by_message(
    mentions: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for mention in mentions:
        message_id = str(mention["message_id"])
        grouped.setdefault(message_id, []).append(mention)
    return grouped


def _message_payload(message, mentions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": message.id,
        "channel_key": message.channel_key,
        "message_type": message.message_type,
        "sender_type": message.sender_type,
        "sender_id": message.sender_id,
        "content": message.content,
        "content_format": message.content_format,
        "reply_to_message_id": message.reply_to_message_id,
        "source_message_id": message.source_message_id,
        "visibility": message.visibility,
        "mentions": mentions,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }


def _job_payload(job) -> dict[str, object]:
    return {
        "id": job.id,
        "channel_key": job.channel_key,
        "assigned_agent_id": job.assigned_agent_id,
        "title": job.title,
        "instructions": job.instructions,
        "status": job.status,
        "priority": job.priority,
        "source_message_id": job.source_message_id,
        "parent_job_id": job.parent_job_id,
        "result_summary": job.result_summary,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _artifact_payload(artifact) -> dict[str, object]:
    return {
        "id": artifact.id,
        "job_id": artifact.job_id,
        "channel_key": artifact.channel_key,
        "source_message_id": artifact.source_message_id,
        "artifact_type": artifact.artifact_type,
        "title": artifact.title,
        "file_name": artifact.file_name,
        "mime_type": artifact.mime_type,
        "size_bytes": artifact.size_bytes,
        "checksum_sha256": artifact.checksum_sha256,
        "created_at": artifact.created_at,
        "updated_at": artifact.updated_at,
    }


@dataclass(frozen=True, slots=True)
class TranscriptExportBundle:
    """Transcript export payload and persisted export row."""

    export: TranscriptExportRecord
    payload: dict[str, object]


class TranscriptExportService:
    """Create transcript exports for a session."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        message_repository: MessageRepository,
        message_mention_repository: MessageMentionRepository,
        job_repository: JobRepository,
        artifact_repository: ArtifactRepository,
        transcript_export_repository: TranscriptExportRepository,
        session_event_repository: SessionEventRepository,
    ) -> None:
        self.session_repository = session_repository
        self.message_repository = message_repository
        self.message_mention_repository = message_mention_repository
        self.job_repository = job_repository
        self.artifact_repository = artifact_repository
        self.transcript_export_repository = transcript_export_repository
        self.session_event_repository = session_event_repository

    async def export_session_transcript(
        self,
        session_id: str,
    ) -> TranscriptExportBundle:
        """Build and persist a transcript export for a session."""

        session = await self.session_repository.get(session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")

        messages = await self.message_repository.list_by_session(session_id)
        jobs = await self.job_repository.list_by_session(session_id)
        artifacts = await self.artifact_repository.list_by_session(session_id)
        mentions = await self.message_mention_repository.list()
        session_message_ids = {message.id for message in messages}
        mentions_by_message = _parse_mentions_by_message(
            [
                asdict(mention)
                for mention in mentions
                if mention.message_id in session_message_ids
            ]
        )
        mention_count = sum(len(items) for items in mentions_by_message.values())

        payload = {
            "schema_version": 1,
            "export_kind": "session_transcript",
            "exported_at": _utc_now(),
            "session": {
                "id": session.id,
                "title": session.title,
                "goal": session.goal,
                "status": session.status,
                "lead_agent_id": session.lead_agent_id,
                "active_phase_id": session.active_phase_id,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            },
            "message_count": len(messages),
            "mention_count": mention_count,
            "job_count": len(jobs),
            "artifact_count": len(artifacts),
            "messages": [
                _message_payload(
                    message,
                    mentions_by_message.get(
                        message.id,
                        [],
                    ),
                )
                for message in messages
            ],
            "jobs": [_job_payload(job) for job in jobs],
            "artifacts": [_artifact_payload(artifact) for artifact in artifacts],
        }
        content_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        now = _utc_now()
        export = TranscriptExportRecord(
            id=f"tex_{uuid4().hex}",
            session_id=session.id,
            export_kind="transcript",
            export_format="json",
            title=f"{session.title} transcript export",
            file_name=f"{session.id}-transcript-{_stamp()}.json",
            mime_type="application/json",
            content_text=content_text,
            size_bytes=len(content_text.encode("utf-8")),
            checksum_sha256=_sha256_hex(content_text),
            metadata_json=json.dumps(
                {
                    "schema_version": 1,
                    "export_format": "json",
                    "message_count": len(messages),
                    "mention_count": mention_count,
                    "job_count": len(jobs),
                    "artifact_count": len(artifacts),
                    "exported_at": now,
                },
                sort_keys=True,
            ),
            created_at=now,
            updated_at=now,
        )
        created = await self.transcript_export_repository.create(export)
        await self.session_event_repository.create(
            SessionEventRecord(
                id=f"evt_{uuid4().hex}",
                session_id=session.id,
                event_type="transcript.exported",
                actor_type="system",
                actor_id=None,
                event_payload_json=json.dumps(
                    {
                        "export_id": created.id,
                        "file_name": created.file_name,
                        "checksum_sha256": created.checksum_sha256,
                        "size_bytes": created.size_bytes,
                    },
                    sort_keys=True,
                ),
                created_at=now,
            )
        )
        return TranscriptExportBundle(export=created, payload=payload)
