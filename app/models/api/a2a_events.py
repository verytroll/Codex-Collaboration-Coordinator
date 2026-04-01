"""API models for the public A2A task event surface."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.a2a_public import A2APublicTaskResponse

A2APublicTaskEventType = Literal[
    "created",
    "status_changed",
    "artifact_attached",
    "phase_changed",
    "review_requested",
    "completed",
]


class A2APublicTaskSubscriptionCreateRequest(BaseModel):
    """Payload for creating a public task subscription."""

    model_config = ConfigDict(extra="forbid")

    since_sequence: int = Field(default=0, ge=0)


class A2APublicTaskSubscriptionResponse(BaseModel):
    """Public subscription payload."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    contract_version: Literal["a2a.public.task.subscription.v1"] = "a2a.public.task.subscription.v1"
    subscription_id: str
    task_id: str
    cursor_sequence: int
    delivery_mode: Literal["sse"] = "sse"
    created_at: str
    updated_at: str


class A2APublicTaskSubscriptionEnvelope(BaseModel):
    """Single subscription response envelope."""

    model_config = ConfigDict(extra="forbid")

    subscription: A2APublicTaskSubscriptionResponse


class A2APublicTaskEventResponse(BaseModel):
    """Public task event payload."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    contract_version: Literal["a2a.public.task.event.v1"] = "a2a.public.task.event.v1"
    event_id: str
    task_id: str
    sequence: int
    event_type: A2APublicTaskEventType
    task: A2APublicTaskResponse
    change: dict[str, Any] | None = None
    created_at: str


class A2APublicTaskEventEnvelope(BaseModel):
    """Single task event response envelope."""

    model_config = ConfigDict(extra="forbid")

    event: A2APublicTaskEventResponse


class A2APublicTaskEventListEnvelope(BaseModel):
    """Public task event list response envelope."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    since_sequence: int
    events: list[A2APublicTaskEventResponse] = Field(default_factory=list)
