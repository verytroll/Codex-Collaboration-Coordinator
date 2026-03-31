"""API models for review mode and relay templates."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.jobs import JobPriority

ReviewDecision = Literal["approved", "changes_requested"]
ReviewScope = Literal["job", "session"]
ReviewStatus = Literal["requested", "approved", "changes_requested"]


class RelayTemplateResponse(BaseModel):
    """Structured relay template metadata."""

    model_config = ConfigDict(extra="forbid")

    template_key: str
    title: str
    source_role: str
    target_role: str
    description: str
    default_channel_key: str
    section_keys: list[str]


class RelayTemplateListEnvelope(BaseModel):
    """Relay template list response envelope."""

    model_config = ConfigDict(extra="forbid")

    templates: list[RelayTemplateResponse]


class RelayTemplateEnvelope(BaseModel):
    """Single relay template response envelope."""

    model_config = ConfigDict(extra="forbid")

    template: RelayTemplateResponse


class ReviewCreateRequest(BaseModel):
    """Payload for starting a review."""

    model_config = ConfigDict(extra="forbid")

    source_job_id: str
    reviewer_agent_id: str | None = None
    review_scope: ReviewScope = "job"
    review_channel_key: str = "review"
    notes: str | None = None


class ReviewDecisionRequest(BaseModel):
    """Payload for resolving a review."""

    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    summary: str | None = None
    required_changes: list[str] = Field(default_factory=list)
    notes: str | None = None
    revision_priority: JobPriority = "normal"
    revision_instructions: str | None = None


class ReviewResponse(BaseModel):
    """Review response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    source_job_id: str
    reviewer_agent_id: str
    requested_by_agent_id: str | None
    review_scope: ReviewScope
    review_status: ReviewStatus
    review_channel_key: str
    template_key: str
    request_message_id: str | None
    decision_message_id: str | None
    summary_artifact_id: str | None
    revision_job_id: str | None
    request_payload: dict[str, Any] | None = None
    decision_payload: dict[str, Any] | None = None
    requested_at: str
    decided_at: str | None
    created_at: str
    updated_at: str


class ReviewEnvelope(BaseModel):
    """Single review response envelope."""

    model_config = ConfigDict(extra="forbid")

    review: ReviewResponse


class ReviewListEnvelope(BaseModel):
    """Review list response envelope."""

    model_config = ConfigDict(extra="forbid")

    reviews: list[ReviewResponse]
