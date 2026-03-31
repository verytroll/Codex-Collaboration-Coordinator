"""API models for session channels."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChannelCreateRequest(BaseModel):
    """Payload for creating a session channel."""

    model_config = ConfigDict(extra="forbid")

    channel_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str | None = None


class ChannelResponse(BaseModel):
    """Session channel response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    channel_key: str
    display_name: str
    description: str | None
    is_default: bool
    sort_order: int
    created_at: str
    updated_at: str


class ChannelEnvelope(BaseModel):
    """Single channel response envelope."""

    model_config = ConfigDict(extra="forbid")

    channel: ChannelResponse


class ChannelListEnvelope(BaseModel):
    """Channel list response envelope."""

    model_config = ConfigDict(extra="forbid")

    channels: list[ChannelResponse]
