"""API models for integration principals and credentials."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.api.identity import ActorRole, ActorType

IntegrationPrincipalType = Literal["integration_client", "service_account"]
IntegrationCredentialScope = Literal["public_read", "public_write", "operator_write"]
IntegrationCredentialStatus = Literal["active", "revoked", "expired"]


class IntegrationPrincipalCreateRequest(BaseModel):
    """Payload for creating an integration principal."""

    model_config = ConfigDict(extra="forbid")

    display_label: str
    principal_type: IntegrationPrincipalType
    actor_role: ActorRole
    actor_type: ActorType = "service"
    default_scopes: list[IntegrationCredentialScope] | None = None
    notes: str | None = None


class IntegrationCredentialIssueRequest(BaseModel):
    """Payload for issuing or rotating a credential."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    scopes: list[IntegrationCredentialScope] | None = None
    expires_at: str | None = None
    note: str | None = None


class IntegrationCredentialStateRequest(BaseModel):
    """Payload for changing a credential's lifecycle state."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None
    note: str | None = None


class IntegrationPrincipalResponse(BaseModel):
    """Integration principal response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_label: str
    principal_type: IntegrationPrincipalType
    actor_role: ActorRole
    actor_type: ActorType
    source: str
    default_scopes: list[IntegrationCredentialScope] = Field(default_factory=list)
    notes: str | None = None
    created_at: str
    updated_at: str


class IntegrationCredentialResponse(BaseModel):
    """Integration credential response payload."""

    model_config = ConfigDict(extra="forbid")

    id: str
    principal_id: str
    label: str
    scopes: list[IntegrationCredentialScope] = Field(default_factory=list)
    status: IntegrationCredentialStatus
    status_reason: str | None = None
    status_note: str | None = None
    expires_at: str | None = None
    revoked_at: str | None = None
    last_used_at: str | None = None
    last_used_surface: str | None = None
    secret_prefix: str
    notes: str | None = None
    created_at: str
    updated_at: str


class IntegrationPrincipalEnvelope(BaseModel):
    """Single integration principal response envelope."""

    model_config = ConfigDict(extra="forbid")

    principal: IntegrationPrincipalResponse


class IntegrationPrincipalListEnvelope(BaseModel):
    """Integration principal list response envelope."""

    model_config = ConfigDict(extra="forbid")

    principals: list[IntegrationPrincipalResponse]


class IntegrationCredentialEnvelope(BaseModel):
    """Single integration credential response envelope."""

    model_config = ConfigDict(extra="forbid")

    credential: IntegrationCredentialResponse
    secret_value: str | None = None
    replaced_credential_id: str | None = None


class IntegrationCredentialListEnvelope(BaseModel):
    """Integration credential list response envelope."""

    model_config = ConfigDict(extra="forbid")

    credentials: list[IntegrationCredentialResponse]
