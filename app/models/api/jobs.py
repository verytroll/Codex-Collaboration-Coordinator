"""API models for jobs and runtime artifacts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JobStatus = Literal[
    "queued",
    "running",
    "input_required",
    "auth_required",
    "completed",
    "failed",
    "canceled",
    "paused_by_loop_guard",
]
JobPriority = Literal["low", "normal", "high"]


class JobResponse(BaseModel):
    """Job response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    channel_key: str
    assigned_agent_id: str
    runtime_id: str | None
    source_message_id: str | None
    parent_job_id: str | None
    title: str
    instructions: str | None
    status: JobStatus
    hop_count: int
    priority: JobPriority
    codex_runtime_id: str | None
    codex_thread_id: str | None
    active_turn_id: str | None
    last_known_turn_status: str | None
    result_summary: str | None
    error_code: str | None
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str


class JobCreateRequest(BaseModel):
    """Payload for creating a direct job."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    assigned_agent_id: str
    title: str
    instructions: str | None = None
    channel_key: str = "general"
    source_message_id: str | None = None
    parent_job_id: str | None = None
    priority: JobPriority = "normal"


class JobEventResponse(BaseModel):
    """Job event payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    job_id: str
    session_id: str
    event_type: str
    event_payload: dict[str, Any] | None = None
    created_at: str


class JobInputResponse(BaseModel):
    """Normalized job input payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    job_id: str
    session_id: str
    input_type: str
    input_payload: dict[str, Any] | None = None
    created_at: str


class ArtifactResponse(BaseModel):
    """Artifact response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    job_id: str
    session_id: str
    channel_key: str
    source_message_id: str | None
    artifact_type: str
    title: str
    content_text: str | None
    file_path: str | None
    file_name: str | None
    mime_type: str | None
    size_bytes: int | None
    checksum_sha256: str | None
    metadata: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class ApprovalRequestResponse(BaseModel):
    """Approval request payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    job_id: str
    agent_id: str
    approval_type: str
    status: str
    request_payload: dict[str, Any]
    decision_payload: dict[str, Any] | None = None
    requested_at: str
    resolved_at: str | None
    created_at: str
    updated_at: str


class JobDetailResponse(BaseModel):
    """Job detail payload."""

    model_config = ConfigDict(extra="forbid")

    job: JobResponse
    inputs: list[JobInputResponse] = Field(default_factory=list)
    events: list[JobEventResponse] = Field(default_factory=list)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    approvals: list[ApprovalRequestResponse] = Field(default_factory=list)


class JobEnvelope(BaseModel):
    """Single job response envelope."""

    model_config = ConfigDict(extra="forbid")

    job: JobDetailResponse


class JobListEnvelope(BaseModel):
    """Job list response envelope."""

    model_config = ConfigDict(extra="forbid")

    jobs: list[JobResponse]


class JobEventListEnvelope(BaseModel):
    """Job event list response envelope."""

    model_config = ConfigDict(extra="forbid")

    events: list[JobEventResponse]


class ArtifactListEnvelope(BaseModel):
    """Artifact list response envelope."""

    model_config = ConfigDict(extra="forbid")

    artifacts: list[ArtifactResponse]


class ApprovalRequestListEnvelope(BaseModel):
    """Approval list response envelope."""

    model_config = ConfigDict(extra="forbid")

    approvals: list[ApprovalRequestResponse]


class JobControlRequest(BaseModel):
    """Payload for control actions on jobs."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class JobInputRequest(BaseModel):
    """Payload for job input."""

    model_config = ConfigDict(extra="forbid")

    input_text: str = Field(min_length=1)
    approval_id: str | None = None


class ApprovalDecisionRequest(BaseModel):
    """Payload for resolving an approval request."""

    model_config = ConfigDict(extra="forbid")

    decision_payload: dict[str, Any] | None = None
