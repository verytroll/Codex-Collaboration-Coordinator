"""API models for artifact exports."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.jobs import ArtifactResponse


class TranscriptExportResponse(BaseModel):
    """Transcript export response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    export_kind: str
    export_format: str
    title: str
    file_name: str
    mime_type: str
    content_text: str
    size_bytes: int
    checksum_sha256: str
    metadata: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class TranscriptExportEnvelope(BaseModel):
    """Single transcript export response envelope."""

    model_config = ConfigDict(extra="forbid")

    transcript_export: TranscriptExportResponse


class TranscriptExportListEnvelope(BaseModel):
    """Transcript export list response envelope."""

    model_config = ConfigDict(extra="forbid")

    transcript_exports: list[TranscriptExportResponse] = Field(default_factory=list)


class SessionArtifactEnvelope(BaseModel):
    """Session artifact listing envelope."""

    model_config = ConfigDict(extra="forbid")

    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    transcript_exports: list[TranscriptExportResponse] = Field(default_factory=list)
