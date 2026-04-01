"""API models for the public A2A task surface."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class A2APublicTaskCreateRequest(BaseModel):
    """Payload for creating or refreshing a public A2A task projection."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)


class A2APublicTaskStatusResponse(BaseModel):
    """Normalized status payload for a public A2A task."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["queued", "in_progress", "blocked", "completed", "failed", "canceled"]
    internal_status: str
    is_terminal: bool
    is_blocked: bool
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str


class A2APublicTaskArtifactResponse(BaseModel):
    """Normalized artifact summary for a public A2A task."""

    model_config = ConfigDict(extra="forbid")

    id: str
    artifact_type: str
    title: str
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    channel_key: str
    is_primary: bool = False


class A2APublicTaskErrorResponse(BaseModel):
    """Normalized error payload for a public A2A task."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class A2APublicTaskResponse(BaseModel):
    """Public A2A task projection payload."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    contract_version: Literal["a2a.public.task.v1"] = "a2a.public.task.v1"
    task_id: str
    context_id: str
    session_id: str
    job_id: str
    phase_id: str | None = None
    phase_key: str | None = None
    phase_title: str | None = None
    phase_template_key: str | None = None
    relay_template_key: str | None = None
    assigned_agent_id: str
    title: str
    summary: str | None = None
    status: A2APublicTaskStatusResponse
    artifacts: list[A2APublicTaskArtifactResponse] = Field(default_factory=list)
    error: A2APublicTaskErrorResponse | None = None
    metadata: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class A2APublicTaskEnvelope(BaseModel):
    """Single public A2A task response envelope."""

    model_config = ConfigDict(extra="forbid")

    task: A2APublicTaskResponse


class A2APublicTaskListEnvelope(BaseModel):
    """Public A2A task list response envelope."""

    model_config = ConfigDict(extra="forbid")

    tasks: list[A2APublicTaskResponse] = Field(default_factory=list)
