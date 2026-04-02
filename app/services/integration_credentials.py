"""Integration principal and credential lifecycle services."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import uuid4

from app.core.errors import ConflictError, NotFoundError
from app.models.api.identity import ActorRole
from app.repositories.integration_credentials import (
    IntegrationCredentialRecord,
    IntegrationCredentialRepository,
    IntegrationPrincipalRecord,
    IntegrationPrincipalRepository,
)
from app.services.authz_service import ActorIdentity

_VALID_PRINCIPAL_TYPES = {"integration_client", "service_account"}
_VALID_CREDENTIAL_SCOPES = {"public_read", "public_write", "operator_write"}
_VALID_ACTOR_ROLES = {"operator", "reviewer", "integration_client", "admin"}
_SCOPE_IMPLICATIONS: dict[str, set[str]] = {
    "public_write": {"public_read"},
    "operator_write": {"public_write", "public_read"},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized.removesuffix("Z") + "+00:00"
    return datetime.fromisoformat(normalized)


def _normalize_scopes(
    scopes: Iterable[str] | None,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if scopes is None:
        return () if allow_empty else ("public_read",)
    normalized: list[str] = []
    for scope in scopes:
        candidate = scope.strip()
        if not candidate:
            continue
        if candidate not in _VALID_CREDENTIAL_SCOPES:
            raise ValueError(f"Unsupported credential scope: {candidate}")
        if candidate not in normalized:
            normalized.append(candidate)
    if not normalized:
        return () if allow_empty else ("public_read",)
    return tuple(normalized)


def _expand_scopes(scopes: Sequence[str]) -> set[str]:
    expanded = set(scopes)
    for scope in scopes:
        expanded.update(_SCOPE_IMPLICATIONS.get(scope, set()))
    return expanded


def _json_dump_scopes(scopes: Sequence[str]) -> str:
    return json.dumps(list(scopes), sort_keys=False)


def _json_load_scopes(scopes_json: str) -> tuple[str, ...]:
    try:
        loaded = json.loads(scopes_json)
    except json.JSONDecodeError:
        return ()
    if not isinstance(loaded, list):
        return ()
    normalized: list[str] = []
    for scope in loaded:
        if isinstance(scope, str) and scope not in normalized:
            normalized.append(scope)
    return tuple(normalized)


def _hash_secret(secret_value: str) -> str:
    return hashlib.sha256(secret_value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CredentialIssueResult:
    """Issued credential plus one-time secret value."""

    credential: IntegrationCredentialRecord
    secret_value: str
    replaced_credential_id: str | None = None


@dataclass(frozen=True, slots=True)
class CredentialAuthMatch:
    """Result of matching a bearer secret against stored credentials."""

    status: str
    principal: IntegrationPrincipalRecord | None = None
    credential: IntegrationCredentialRecord | None = None
    actor_identity: ActorIdentity | None = None


class IntegrationCredentialService:
    """Manage integration principals and credentials."""

    def __init__(
        self,
        *,
        principal_repository: IntegrationPrincipalRepository,
        credential_repository: IntegrationCredentialRepository,
    ) -> None:
        self.principal_repository = principal_repository
        self.credential_repository = credential_repository

    async def create_principal(
        self,
        *,
        display_label: str,
        principal_type: str,
        actor_role: ActorRole,
        actor_type: str = "service",
        default_scopes: Sequence[str] | None = None,
        notes: str | None = None,
    ) -> IntegrationPrincipalRecord:
        """Create a new integration principal."""
        self._validate_principal_type(principal_type)
        self._validate_actor_role(actor_role)
        normalized_actor_type = actor_type.strip().lower()
        if normalized_actor_type not in {"human", "service"}:
            raise ValueError(f"Unsupported actor type: {actor_type}")
        if default_scopes is None:
            resolved_default_scopes = (
                ("public_read",) if actor_role == "integration_client" else ("operator_write",)
            )
        else:
            resolved_default_scopes = _normalize_scopes(default_scopes, allow_empty=True)
        now = _utc_now()
        principal = IntegrationPrincipalRecord(
            id=f"ipr_{uuid4().hex}",
            display_label=display_label.strip(),
            principal_type=principal_type,
            actor_role=actor_role,
            actor_type=normalized_actor_type,
            source="managed",
            default_scopes_json=_json_dump_scopes(resolved_default_scopes),
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        return await self.principal_repository.create(principal)

    async def list_principals(self) -> list[IntegrationPrincipalRecord]:
        """List principals in creation order."""
        return await self.principal_repository.list()

    async def get_principal(self, principal_id: str) -> IntegrationPrincipalRecord:
        """Load a principal or raise if it is missing."""
        principal = await self.principal_repository.get(principal_id)
        if principal is None:
            raise NotFoundError(f"Integration principal not found: {principal_id}")
        return principal

    async def list_credentials(
        self,
        *,
        principal_id: str | None = None,
    ) -> list[IntegrationCredentialRecord]:
        """List credentials, optionally scoped to a principal."""
        if principal_id is None:
            return await self.credential_repository.list()
        return await self.credential_repository.list_by_principal(principal_id)

    async def get_credential(self, credential_id: str) -> IntegrationCredentialRecord:
        """Load a credential or raise if it is missing."""
        credential = await self.credential_repository.get(credential_id)
        if credential is None:
            raise NotFoundError(f"Integration credential not found: {credential_id}")
        return credential

    async def issue_credential(
        self,
        *,
        principal_id: str,
        label: str | None = None,
        scopes: Sequence[str] | None = None,
        expires_at: str | None = None,
        note: str | None = None,
    ) -> CredentialIssueResult:
        """Issue a new bearer credential for a principal."""
        principal = await self.get_principal(principal_id)
        if scopes is None:
            resolved_scopes = _normalize_scopes(
                _json_load_scopes(principal.default_scopes_json),
                allow_empty=True,
            )
        else:
            resolved_scopes = _normalize_scopes(scopes, allow_empty=True)
        resolved_expires_at = self._validate_expires_at(expires_at)
        secret_value = secrets.token_urlsafe(32)
        now = _utc_now()
        credential = IntegrationCredentialRecord(
            id=f"icr_{uuid4().hex}",
            principal_id=principal.id,
            label=(
                label.strip() if label is not None and label.strip() else principal.display_label
            ),
            secret_hash=_hash_secret(secret_value),
            secret_prefix=secret_value[:8],
            scopes_json=_json_dump_scopes(resolved_scopes),
            status="active",
            status_reason=None,
            status_note=None,
            expires_at=resolved_expires_at,
            revoked_at=None,
            last_used_at=None,
            last_used_surface=None,
            notes=note,
            created_at=now,
            updated_at=now,
        )
        created = await self.credential_repository.create(credential)
        return CredentialIssueResult(credential=created, secret_value=secret_value)

    async def rotate_credential(
        self,
        credential_id: str,
        *,
        label: str | None = None,
        scopes: Sequence[str] | None = None,
        expires_at: str | None = None,
        note: str | None = None,
    ) -> CredentialIssueResult:
        """Rotate an active credential by revoking the old secret and issuing a new one."""
        credential = await self.get_credential(credential_id)
        if credential.status != "active":
            raise ConflictError(
                f"Credential {credential_id} cannot be rotated from status {credential.status}"
            )
        principal = await self.get_principal(credential.principal_id)
        if scopes is None:
            resolved_scopes = _normalize_scopes(
                _json_load_scopes(credential.scopes_json),
                allow_empty=True,
            )
        else:
            resolved_scopes = _normalize_scopes(scopes, allow_empty=True)
        resolved_expires_at = self._validate_expires_at(
            expires_at if expires_at is not None else credential.expires_at
        )
        now = _utc_now()
        revoked = replace(
            credential,
            status="revoked",
            status_reason="rotated",
            status_note=note,
            revoked_at=now,
            updated_at=now,
        )
        secret_value = secrets.token_urlsafe(32)
        rotated = IntegrationCredentialRecord(
            id=f"icr_{uuid4().hex}",
            principal_id=principal.id,
            label=(label.strip() if label is not None and label.strip() else credential.label),
            secret_hash=_hash_secret(secret_value),
            secret_prefix=secret_value[:8],
            scopes_json=_json_dump_scopes(resolved_scopes),
            status="active",
            status_reason=None,
            status_note=None,
            expires_at=resolved_expires_at,
            revoked_at=None,
            last_used_at=None,
            last_used_surface=None,
            notes=note if note is not None else credential.notes,
            created_at=now,
            updated_at=now,
        )
        created = await self.credential_repository.rotate(
            revoked=revoked,
            replacement=rotated,
        )
        return CredentialIssueResult(
            credential=created,
            secret_value=secret_value,
            replaced_credential_id=credential.id,
        )

    async def revoke_credential(
        self,
        credential_id: str,
        *,
        reason: str | None = None,
        note: str | None = None,
    ) -> IntegrationCredentialRecord:
        """Revoke a credential."""
        credential = await self.get_credential(credential_id)
        if credential.status == "revoked":
            return credential
        now = _utc_now()
        updated = replace(
            credential,
            status="revoked",
            status_reason=reason or "revoked",
            status_note=note,
            revoked_at=now,
            updated_at=now,
        )
        return await self.credential_repository.update(updated)

    async def expire_credential(
        self,
        credential_id: str,
        *,
        reason: str | None = None,
        note: str | None = None,
    ) -> IntegrationCredentialRecord:
        """Expire a credential immediately."""
        credential = await self.get_credential(credential_id)
        if credential.status == "expired":
            return credential
        now = _utc_now()
        updated = replace(
            credential,
            status="expired",
            status_reason=reason or "expired",
            status_note=note,
            expires_at=credential.expires_at or now,
            updated_at=now,
        )
        return await self.credential_repository.update(updated)

    async def authenticate_secret(
        self,
        secret_value: str,
        *,
        surface: str,
        auth_mode: str,
        client_host: str | None = None,
    ) -> CredentialAuthMatch | None:
        """Resolve a bearer secret into principal and credential metadata."""
        credential = await self.credential_repository.get_by_secret_hash(_hash_secret(secret_value))
        if credential is None:
            return None
        principal = await self.principal_repository.get(credential.principal_id)
        if principal is None:
            return CredentialAuthMatch(
                status="principal_missing",
                principal=None,
                credential=credential,
                actor_identity=None,
            )
        actor_identity = self._build_actor_identity(
            principal,
            credential,
            auth_mode=auth_mode,
            client_host=client_host,
        )
        if credential.status != "active":
            return CredentialAuthMatch(
                status=credential.status,
                principal=principal,
                credential=credential,
                actor_identity=actor_identity,
            )
        if credential.expires_at is not None:
            try:
                if self._is_past_due(credential.expires_at):
                    expired = replace(
                        credential,
                        status="expired",
                        status_reason="expired",
                        status_note=credential.status_note,
                        updated_at=_utc_now(),
                    )
                    credential = await self.credential_repository.update(expired)
                    return CredentialAuthMatch(
                        status="expired",
                        principal=principal,
                        credential=credential,
                        actor_identity=actor_identity,
                    )
            except (TypeError, ValueError):
                return CredentialAuthMatch(
                    status="invalid_expires_at",
                    principal=principal,
                    credential=credential,
                    actor_identity=actor_identity,
                )
        credential = await self._mark_credential_used(
            credential,
            surface=surface,
        )
        return CredentialAuthMatch(
            status="active",
            principal=principal,
            credential=credential,
            actor_identity=actor_identity,
        )

    def _build_actor_identity(
        self,
        principal: IntegrationPrincipalRecord,
        credential: IntegrationCredentialRecord,
        *,
        auth_mode: str,
        client_host: str | None,
    ) -> ActorIdentity:
        credential_scopes = tuple(sorted(_expand_scopes(_json_load_scopes(credential.scopes_json))))
        return ActorIdentity(
            principal_id=principal.id,
            credential_id=credential.id,
            actor_id=principal.id,
            actor_role=principal.actor_role,
            actor_type=principal.actor_type,
            display_label=principal.display_label,
            source="credentials",
            auth_mode=auth_mode,
            client_host=client_host,
            credential_scopes=credential_scopes,
            credential_status=credential.status,
        )

    async def _mark_credential_used(
        self,
        credential: IntegrationCredentialRecord,
        *,
        surface: str,
    ) -> IntegrationCredentialRecord:
        now = _utc_now()
        updated = replace(
            credential,
            last_used_at=now,
            last_used_surface=surface,
            updated_at=now,
        )
        return await self.credential_repository.update(updated)

    def _validate_principal_type(self, principal_type: str) -> None:
        if principal_type not in _VALID_PRINCIPAL_TYPES:
            raise ValueError(f"Unsupported principal type: {principal_type}")

    def _validate_actor_role(self, actor_role: ActorRole) -> None:
        if actor_role not in _VALID_ACTOR_ROLES:
            raise ValueError(f"Unsupported actor role: {actor_role}")

    def _is_past_due(self, expires_at: str) -> bool:
        expires_at_value = _parse_iso_datetime(expires_at)
        if expires_at_value.tzinfo is None or expires_at_value.utcoffset() is None:
            raise ValueError("expires_at must include a timezone offset")
        return expires_at_value <= datetime.now(timezone.utc)

    def _validate_expires_at(self, expires_at: str | None) -> str | None:
        if expires_at is None:
            return None
        normalized = expires_at.strip()
        if not normalized:
            raise ValueError("expires_at must be a timezone-aware ISO 8601 datetime")
        parsed = _parse_iso_datetime(normalized)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("expires_at must include a timezone offset")
        return normalized
