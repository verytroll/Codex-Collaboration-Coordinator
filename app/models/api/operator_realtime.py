"""API models for the operator realtime activity surface."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

OperatorActivityCategory = Literal[
    "message",
    "job",
    "phase",
    "approval",
    "review",
    "runtime",
    "participant",
    "system",
]
OperatorActivitySeverity = Literal["info", "warning", "critical"]


class OperatorSessionActivityEventResponse(BaseModel):
    """Replayable operator activity event."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    contract_version: Literal["operator.session.activity.event.v1"] = (
        "operator.session.activity.event.v1"
    )
    sequence: int
    event_type: str
    category: OperatorActivityCategory
    severity: OperatorActivitySeverity
    title: str
    detail: str | None = None
    session_id: str
    entity_type: str
    entity_id: str
    job_id: str | None = None
    phase_key: str | None = None
    runtime_pool_key: str | None = None
    approval_id: str | None = None
    message_id: str | None = None
    actor_type: str | None = None
    actor_id: str | None = None
    payload: dict[str, Any] | None = None
    created_at: str


class OperatorActivitySignalResponse(BaseModel):
    """Short summary of an operational signal."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    title: str
    detail: str | None = None
    severity: OperatorActivitySeverity = "info"
    count: int | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    created_at: str | None = None


class OperatorSessionActivitySignalsResponse(BaseModel):
    """Grouped operational signals for the selected session."""

    model_config = ConfigDict(extra="forbid")

    pending_approvals: list[OperatorActivitySignalResponse] = Field(default_factory=list)
    recent_errors: list[OperatorActivitySignalResponse] = Field(default_factory=list)
    stuck_jobs: list[OperatorActivitySignalResponse] = Field(default_factory=list)
    phase_bottlenecks: list[OperatorActivitySignalResponse] = Field(default_factory=list)
    runtime_health: list[OperatorActivitySignalResponse] = Field(default_factory=list)


class OperatorSessionActivityResponse(BaseModel):
    """Replayable operator activity feed for a session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    since_sequence: int
    next_cursor_sequence: int
    total_events: int
    generated_at: str
    events: list[OperatorSessionActivityEventResponse] = Field(default_factory=list)
    signals: OperatorSessionActivitySignalsResponse
