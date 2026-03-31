"""Artifact creation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.jobs import JobEventRecord, JobEventRepository, JobRecord


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_text(payload: dict[str, object], job: JobRecord) -> str | None:
    for key in ("output_text", "output", "content", "message", "text", "summary"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if job.result_summary and job.result_summary.strip():
        return job.result_summary.strip()
    return None


@dataclass(frozen=True, slots=True)
class ArtifactBundle:
    """Artifacts produced from a turn response."""

    artifacts: list[ArtifactRecord]


class ArtifactManager:
    """Persist artifacts emitted by Codex outputs."""

    def __init__(
        self,
        *,
        artifact_repository: ArtifactRepository,
        job_event_repository: JobEventRepository,
    ) -> None:
        self.artifact_repository = artifact_repository
        self.job_event_repository = job_event_repository

    async def create_artifacts_from_turn(
        self,
        *,
        job: JobRecord,
        payload: dict[str, object],
        created_at: str | None = None,
    ) -> ArtifactBundle:
        """Create artifact rows from a Codex turn payload."""
        now = created_at or _utc_now()
        artifacts: list[ArtifactRecord] = []
        text = _extract_text(payload, job)
        if text is not None:
            artifacts.append(
                await self._create_artifact(
                    job=job,
                    artifact_type="final_text",
                    title=f"{job.title} output",
                    content_text=text,
                    file_path=None,
                    file_name=None,
                    mime_type="text/plain",
                    size_bytes=len(text.encode("utf-8")),
                    checksum_sha256=None,
                    metadata_json=None,
                    created_at=now,
                )
            )

        diff_text = payload.get("diff")
        if isinstance(diff_text, str) and diff_text.strip():
            artifacts.append(
                await self._create_artifact(
                    job=job,
                    artifact_type="diff",
                    title=f"{job.title} diff",
                    content_text=diff_text.strip(),
                    file_path=None,
                    file_name=None,
                    mime_type="text/x-diff",
                    size_bytes=len(diff_text.encode("utf-8")),
                    checksum_sha256=None,
                    metadata_json=None,
                    created_at=now,
                )
            )

        files = payload.get("files")
        if isinstance(files, list):
            for file_payload in files:
                if not isinstance(file_payload, dict):
                    continue
                artifacts.append(
                    await self._create_artifact(
                        job=job,
                        artifact_type="file",
                        title=str(
                            file_payload.get("title")
                            or file_payload.get("file_name")
                            or "File artifact"
                        ),
                        content_text=(
                            file_payload.get("content_text")
                            if isinstance(file_payload.get("content_text"), str)
                            else None
                        ),
                        file_path=(
                            file_payload.get("file_path")
                            if isinstance(file_payload.get("file_path"), str)
                            else None
                        ),
                        file_name=(
                            file_payload.get("file_name")
                            if isinstance(file_payload.get("file_name"), str)
                            else None
                        ),
                        mime_type=(
                            file_payload.get("mime_type")
                            if isinstance(file_payload.get("mime_type"), str)
                            else None
                        ),
                        size_bytes=(
                            int(file_payload["size_bytes"])
                            if isinstance(file_payload.get("size_bytes"), int)
                            else None
                        ),
                        checksum_sha256=(
                            file_payload.get("checksum_sha256")
                            if isinstance(file_payload.get("checksum_sha256"), str)
                            else None
                        ),
                        metadata_json=json.dumps(file_payload, sort_keys=True),
                        created_at=now,
                    )
                )

        return ArtifactBundle(artifacts=artifacts)

    async def _create_artifact(
        self,
        *,
        job: JobRecord,
        artifact_type: str,
        title: str,
        content_text: str | None,
        file_path: str | None,
        file_name: str | None,
        mime_type: str | None,
        size_bytes: int | None,
        checksum_sha256: str | None,
        metadata_json: str | None,
        created_at: str,
    ) -> ArtifactRecord:
        artifact = ArtifactRecord(
            id=f"art_{uuid4().hex}",
            job_id=job.id,
            session_id=job.session_id,
            channel_key=job.channel_key,
            source_message_id=job.source_message_id,
            artifact_type=artifact_type,
            title=title[:120],
            content_text=content_text,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            metadata_json=metadata_json,
            created_at=created_at,
            updated_at=created_at,
        )
        created = await self.artifact_repository.create(artifact)
        await self.job_event_repository.create(
            JobEventRecord(
                id=f"jbe_{uuid4().hex}",
                job_id=job.id,
                session_id=job.session_id,
                event_type="artifact.created",
                event_payload_json=json.dumps(
                    {
                        "artifact_id": created.id,
                        "artifact_type": artifact_type,
                        "title": created.title,
                    },
                    sort_keys=True,
                ),
                created_at=created_at,
            )
        )
        return created
