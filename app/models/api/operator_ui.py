"""API models for the thin operator UI shell."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.artifacts import TranscriptExportResponse
from app.models.api.jobs import ApprovalRequestResponse, ArtifactResponse, JobResponse
from app.models.api.messages import MessageResponse
from app.models.api.operator_dashboard import (
    OperatorDashboardFiltersResponse,
    OperatorDashboardResponse,
)
from app.models.api.participants import ParticipantResponse
from app.models.api.phases import PhaseResponse
from app.models.api.sessions import SessionResponse


class OperatorSessionSummaryResponse(BaseModel):
    """Compact operator-facing session summary."""

    model_config = ConfigDict(extra="forbid")

    session: SessionResponse
    template_key: str | None = None
    loop_guard_status: str
    loop_guard_reason: str | None = None
    last_message_at: str | None = None
    phase_count: int
    message_count: int
    job_count: int
    approval_count: int
    artifact_count: int


class OperatorSessionDetailResponse(OperatorSessionSummaryResponse):
    """Expanded session payload for the operator shell."""

    model_config = ConfigDict(extra="forbid")

    phases: list[PhaseResponse] = Field(default_factory=list)
    participants: list[ParticipantResponse] = Field(default_factory=list)
    messages: list[MessageResponse] = Field(default_factory=list)
    jobs: list[JobResponse] = Field(default_factory=list)
    approvals: list[ApprovalRequestResponse] = Field(default_factory=list)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    transcript_exports: list[TranscriptExportResponse] = Field(default_factory=list)


class OperatorShellResponse(BaseModel):
    """Bootstrap payload for the operator UI shell."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    filters: OperatorDashboardFiltersResponse
    dashboard: OperatorDashboardResponse
    sessions: list[OperatorSessionSummaryResponse] = Field(default_factory=list)
    selected_session_id: str | None = None
    selected_session: OperatorSessionDetailResponse | None = None
