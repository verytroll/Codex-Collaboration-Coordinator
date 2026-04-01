"""Artifact and transcript export routes."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_artifact_repository,
    get_session_repository,
    get_transcript_export_repository,
    get_transcript_export_service,
)
from app.models.api.artifacts import (
    SessionArtifactEnvelope,
    TranscriptExportEnvelope,
    TranscriptExportResponse,
)
from app.models.api.jobs import ArtifactResponse
from app.repositories.artifacts import ArtifactRecord, ArtifactRepository
from app.repositories.sessions import SessionRepository
from app.repositories.transcript_exports import (
    TranscriptExportRecord,
    TranscriptExportRepository,
)
from app.services.transcript_export import TranscriptExportBundle, TranscriptExportService

router = APIRouter(prefix="/api/v1", tags=["artifacts"])


def _parse_json(payload: str | None) -> dict[str, object] | None:
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload}
    return data if isinstance(data, dict) else {"value": data}


def _artifact_response(artifact: ArtifactRecord) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact.id,
        job_id=artifact.job_id,
        session_id=artifact.session_id,
        channel_key=artifact.channel_key,
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


def _transcript_export_response(
    transcript_export: TranscriptExportRecord,
) -> TranscriptExportResponse:
    return TranscriptExportResponse(
        id=transcript_export.id,
        session_id=transcript_export.session_id,
        export_kind=transcript_export.export_kind,
        export_format=transcript_export.export_format,
        title=transcript_export.title,
        file_name=transcript_export.file_name,
        mime_type=transcript_export.mime_type,
        content_text=transcript_export.content_text,
        size_bytes=transcript_export.size_bytes,
        checksum_sha256=transcript_export.checksum_sha256,
        metadata=_parse_json(transcript_export.metadata_json),
        created_at=transcript_export.created_at,
        updated_at=transcript_export.updated_at,
    )


async def _ensure_session(session_repository: SessionRepository, session_id: str) -> None:
    if await session_repository.get(session_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )


@router.get("/sessions/{session_id}/artifacts", response_model=SessionArtifactEnvelope)
async def list_session_artifacts(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    transcript_export_repository: Annotated[
        TranscriptExportRepository,
        Depends(get_transcript_export_repository),
    ],
) -> SessionArtifactEnvelope:
    await _ensure_session(session_repository, session_id)
    return SessionArtifactEnvelope(
        artifacts=[
            _artifact_response(artifact)
            for artifact in await artifact_repository.list_by_session(session_id)
        ],
        transcript_exports=[
            _transcript_export_response(export)
            for export in await transcript_export_repository.list_by_session(session_id)
        ],
    )


@router.post(
    "/sessions/{session_id}/transcript-export",
    response_model=TranscriptExportEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_transcript_export(
    session_id: str,
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    transcript_export_service: Annotated[
        TranscriptExportService,
        Depends(get_transcript_export_service),
    ],
) -> TranscriptExportEnvelope:
    await _ensure_session(session_repository, session_id)
    try:
        bundle: TranscriptExportBundle = await transcript_export_service.export_session_transcript(
            session_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return TranscriptExportEnvelope(transcript_export=_transcript_export_response(bundle.export))


@router.get("/transcript-exports/{export_id}", response_model=TranscriptExportEnvelope)
async def get_transcript_export(
    export_id: str,
    transcript_export_repository: Annotated[
        TranscriptExportRepository,
        Depends(get_transcript_export_repository),
    ],
) -> TranscriptExportEnvelope:
    transcript_export = await transcript_export_repository.get(export_id)
    if transcript_export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript export not found: {export_id}",
        )
    return TranscriptExportEnvelope(
        transcript_export=_transcript_export_response(transcript_export)
    )
