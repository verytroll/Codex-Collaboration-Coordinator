"""Operator routes for integration principals and credential lifecycle."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_authz_service,
    get_integration_credential_service,
    get_operator_actor_identity,
)
from app.models.api.integration_credentials import (
    IntegrationCredentialEnvelope,
    IntegrationCredentialIssueRequest,
    IntegrationCredentialListEnvelope,
    IntegrationCredentialResponse,
    IntegrationCredentialStateRequest,
    IntegrationPrincipalCreateRequest,
    IntegrationPrincipalEnvelope,
    IntegrationPrincipalListEnvelope,
    IntegrationPrincipalResponse,
)
from app.services.authz_service import ActorIdentity, AuthzService
from app.services.integration_credentials import IntegrationCredentialService

router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


def _load_scopes(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str)]


def _principal_response(principal) -> IntegrationPrincipalResponse:
    return IntegrationPrincipalResponse(
        id=principal.id,
        display_label=principal.display_label,
        principal_type=principal.principal_type,
        actor_role=principal.actor_role,
        actor_type=principal.actor_type,
        source=principal.source,
        default_scopes=_load_scopes(principal.default_scopes_json),
        notes=principal.notes,
        created_at=principal.created_at,
        updated_at=principal.updated_at,
    )


def _credential_response(credential) -> IntegrationCredentialResponse:
    return IntegrationCredentialResponse(
        id=credential.id,
        principal_id=credential.principal_id,
        label=credential.label,
        scopes=_load_scopes(credential.scopes_json),
        status=credential.status,
        status_reason=credential.status_reason,
        status_note=credential.status_note,
        expires_at=credential.expires_at,
        revoked_at=credential.revoked_at,
        last_used_at=credential.last_used_at,
        last_used_surface=credential.last_used_surface,
        secret_prefix=credential.secret_prefix,
        notes=credential.notes,
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


def _build_principal_envelope(principal) -> IntegrationPrincipalEnvelope:
    return IntegrationPrincipalEnvelope(principal=_principal_response(principal))


def _build_principal_list_envelope(principals) -> IntegrationPrincipalListEnvelope:
    return IntegrationPrincipalListEnvelope(
        principals=[_principal_response(principal) for principal in principals]
    )


def _build_credential_envelope(
    credential,
    *,
    secret_value: str | None = None,
    replaced_credential_id: str | None = None,
) -> IntegrationCredentialEnvelope:
    return IntegrationCredentialEnvelope(
        credential=_credential_response(credential),
        secret_value=secret_value,
        replaced_credential_id=replaced_credential_id,
    )


def _build_credential_list_envelope(credentials) -> IntegrationCredentialListEnvelope:
    return IntegrationCredentialListEnvelope(
        credentials=[_credential_response(credential) for credential in credentials]
    )


@router.post(
    "/integration-principals",
    response_model=IntegrationPrincipalEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_principal(
    payload: IntegrationPrincipalCreateRequest,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
) -> IntegrationPrincipalEnvelope:
    authz_service.require_operator_action(actor_identity, action="manage_integration_principal")
    try:
        principal = await credential_service.create_principal(
            display_label=payload.display_label,
            principal_type=payload.principal_type,
            actor_role=payload.actor_role,
            actor_type=payload.actor_type,
            default_scopes=payload.default_scopes,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_principal_envelope(principal)


@router.get("/integration-principals", response_model=IntegrationPrincipalListEnvelope)
async def list_principals(
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
) -> IntegrationPrincipalListEnvelope:
    authz_service.require_operator_action(actor_identity, action="list_integration_principals")
    principals = await credential_service.list_principals()
    return _build_principal_list_envelope(principals)


@router.get(
    "/integration-principals/{principal_id}",
    response_model=IntegrationPrincipalEnvelope,
)
async def get_principal(
    principal_id: str,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
) -> IntegrationPrincipalEnvelope:
    authz_service.require_operator_action(actor_identity, action="view_integration_principal")
    try:
        principal = await credential_service.get_principal(principal_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_principal_envelope(principal)


@router.get(
    "/integration-principals/{principal_id}/credentials",
    response_model=IntegrationCredentialListEnvelope,
)
async def list_credentials_for_principal(
    principal_id: str,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
) -> IntegrationCredentialListEnvelope:
    authz_service.require_operator_action(actor_identity, action="list_integration_credentials")
    try:
        await credential_service.get_principal(principal_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    credentials = await credential_service.list_credentials(principal_id=principal_id)
    return _build_credential_list_envelope(credentials)


@router.post(
    "/integration-principals/{principal_id}/credentials",
    response_model=IntegrationCredentialEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def issue_credential(
    principal_id: str,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    payload: IntegrationCredentialIssueRequest | None = None,
) -> IntegrationCredentialEnvelope:
    authz_service.require_operator_action(actor_identity, action="issue_integration_credential")
    try:
        result = await credential_service.issue_credential(
            principal_id=principal_id,
            label=payload.label if payload is not None else None,
            scopes=payload.scopes if payload is not None else None,
            expires_at=payload.expires_at if payload is not None else None,
            note=payload.note if payload is not None else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_credential_envelope(
        result.credential,
        secret_value=result.secret_value,
    )


@router.get(
    "/integration-credentials/{credential_id}",
    response_model=IntegrationCredentialEnvelope,
)
async def get_credential(
    credential_id: str,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
) -> IntegrationCredentialEnvelope:
    authz_service.require_operator_action(actor_identity, action="view_integration_credential")
    try:
        credential = await credential_service.get_credential(credential_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_credential_envelope(credential)


@router.post(
    "/integration-credentials/{credential_id}/rotate",
    response_model=IntegrationCredentialEnvelope,
)
async def rotate_credential(
    credential_id: str,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    payload: IntegrationCredentialIssueRequest | None = None,
) -> IntegrationCredentialEnvelope:
    authz_service.require_operator_action(actor_identity, action="rotate_integration_credential")
    try:
        result = await credential_service.rotate_credential(
            credential_id,
            label=payload.label if payload is not None else None,
            scopes=payload.scopes if payload is not None else None,
            expires_at=payload.expires_at if payload is not None else None,
            note=payload.note if payload is not None else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_credential_envelope(
        result.credential,
        secret_value=result.secret_value,
        replaced_credential_id=result.replaced_credential_id,
    )


@router.post(
    "/integration-credentials/{credential_id}/revoke",
    response_model=IntegrationCredentialEnvelope,
)
async def revoke_credential(
    credential_id: str,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    payload: IntegrationCredentialStateRequest | None = None,
) -> IntegrationCredentialEnvelope:
    authz_service.require_operator_action(actor_identity, action="revoke_integration_credential")
    try:
        credential = await credential_service.revoke_credential(
            credential_id,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_credential_envelope(credential)


@router.post(
    "/integration-credentials/{credential_id}/expire",
    response_model=IntegrationCredentialEnvelope,
)
async def expire_credential(
    credential_id: str,
    credential_service: Annotated[
        IntegrationCredentialService,
        Depends(get_integration_credential_service),
    ],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    payload: IntegrationCredentialStateRequest | None = None,
) -> IntegrationCredentialEnvelope:
    authz_service.require_operator_action(actor_identity, action="expire_integration_credential")
    try:
        credential = await credential_service.expire_credential(
            credential_id,
            reason=payload.reason if payload is not None else None,
            note=payload.note if payload is not None else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_credential_envelope(credential)
