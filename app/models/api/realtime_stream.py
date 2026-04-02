"""API models for SSE streaming envelopes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.a2a_events import A2APublicTaskEventResponse


class A2APublicTaskEventStreamEnvelope(BaseModel):
    """Replayable public task event stream payload."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    contract_version: Literal["a2a.public.task.event.stream.v1"] = (
        "a2a.public.task.event.stream.v1"
    )
    task_id: str
    since_sequence: int
    next_cursor_sequence: int
    delivery_mode: Literal["sse"] = "sse"
    generated_at: str
    events: list[A2APublicTaskEventResponse] = Field(default_factory=list)
