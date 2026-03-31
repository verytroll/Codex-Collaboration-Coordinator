"""API models for messages."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MessageSenderType = Literal["user", "agent", "system"]
MessageType = Literal[
    "chat",
    "command",
    "relay",
    "status",
    "approval_request",
    "approval_decision",
    "artifact_notice",
]


class MessageCreateRequest(BaseModel):
    """Payload for creating a session message."""

    model_config = ConfigDict(extra="forbid")

    sender_type: MessageSenderType
    sender_id: str | None = None
    content: str = Field(min_length=1)
    reply_to_message_id: str | None = None
    message_type: MessageType = "chat"
    channel_key: str = "general"


class MessageResponse(BaseModel):
    """Message response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    channel_key: str
    sender_type: MessageSenderType
    sender_id: str | None
    content: str
    message_type: MessageType
    reply_to_message_id: str | None
    mentions: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    created_at: str


class MessageRoutingResponse(BaseModel):
    """Message routing summary."""

    model_config = ConfigDict(extra="forbid")

    detected_mentions: list[str] = Field(default_factory=list)
    created_jobs: list[str] = Field(default_factory=list)


class MessageEnvelope(BaseModel):
    """Single message response envelope."""

    model_config = ConfigDict(extra="forbid")

    message: MessageResponse


class MessageCreateEnvelope(BaseModel):
    """Message creation response envelope."""

    model_config = ConfigDict(extra="forbid")

    message: MessageResponse
    routing: MessageRoutingResponse


class MessageListEnvelope(BaseModel):
    """Message list response envelope."""

    model_config = ConfigDict(extra="forbid")

    messages: list[MessageResponse]
