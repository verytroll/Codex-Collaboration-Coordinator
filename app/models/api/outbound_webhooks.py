"""API models for outbound webhook registrations and deliveries."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OutboundWebhookStatus = Literal["active", "disabled"]
OutboundWebhookDeliveryStatus = Literal["pending", "retrying", "delivered", "failed"]


class OutboundWebhookCreateRequest(BaseModel):
    """Payload for creating a managed outbound webhook registration."""

    model_config = ConfigDict(extra="forbid")

    target_url: str
    signing_secret: str | None = None
    description: str | None = None


class OutboundWebhookDisableRequest(BaseModel):
    """Payload for disabling an outbound webhook registration."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class OutboundWebhookRegistrationResponse(BaseModel):
    """Outbound webhook registration response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    task_id: str
    session_id: str
    target_url: str
    status: OutboundWebhookStatus
    description: str | None = None
    signing_secret_prefix: str
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_error_message: str | None = None
    failure_count: int
    last_delivered_sequence: int
    created_at: str
    updated_at: str


class OutboundWebhookDeliveryResponse(BaseModel):
    """Outbound webhook delivery response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    registration_id: str
    task_id: str
    session_id: str
    event_id: str
    event_sequence: int
    event_type: str
    status: OutboundWebhookDeliveryStatus
    attempt_count: int
    next_attempt_at: str
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_response_status: int | None = None
    last_error_message: str | None = None
    created_at: str
    updated_at: str


class OutboundWebhookEnvelope(BaseModel):
    """Single outbound webhook response envelope."""

    model_config = ConfigDict(extra="forbid")

    webhook: OutboundWebhookRegistrationResponse
    signing_secret: str | None = None


class OutboundWebhookListEnvelope(BaseModel):
    """Outbound webhook list response envelope."""

    model_config = ConfigDict(extra="forbid")

    webhooks: list[OutboundWebhookRegistrationResponse] = Field(default_factory=list)


class OutboundWebhookDeliveryListEnvelope(BaseModel):
    """Outbound webhook delivery list response envelope."""

    model_config = ConfigDict(extra="forbid")

    deliveries: list[OutboundWebhookDeliveryResponse] = Field(default_factory=list)
