"""API models for the experimental A2A adapter bridge."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class A2AAdapterArtifactResponse(BaseModel):
    """Artifact summary projected into an A2A task."""

    model_config = ConfigDict(extra="forbid")

    id: str
    artifact_type: str
    title: str
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    channel_key: str


class A2ATaskResponse(BaseModel):
    """A2A task projection payload."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    session_id: str
    job_id: str
    phase_id: str | None = None
    phase_key: str | None = None
    phase_title: str | None = None
    context_id: str
    status: str
    title: str
    summary: str | None = None
    relay_template_key: str | None = None
    assigned_agent_id: str
    artifacts: list[A2AAdapterArtifactResponse] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class A2ATaskEnvelope(BaseModel):
    """Single A2A task response envelope."""

    model_config = ConfigDict(extra="forbid")

    task: A2ATaskResponse


class A2ATaskListEnvelope(BaseModel):
    """A2A task list response envelope."""

    model_config = ConfigDict(extra="forbid")

    tasks: list[A2ATaskResponse] = Field(default_factory=list)
