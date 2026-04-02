"""Operator routes for outbound webhook registrations and deliveries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_authz_service,
    get_operator_actor_identity,
    get_outbound_webhook_service,
)
from app.models.api.outbound_webhooks import (
    OutboundWebhookCreateRequest,
    OutboundWebhookDeliveryListEnvelope,
    OutboundWebhookDeliveryResponse,
    OutboundWebhookDisableRequest,
    OutboundWebhookEnvelope,
    OutboundWebhookListEnvelope,
    OutboundWebhookRegistrationResponse,
)
from app.services.authz_service import ActorIdentity, AuthzService
from app.services.outbound_webhooks import OutboundWebhookService

router = APIRouter(prefix="/api/v1/operator/a2a/tasks", tags=["operator"])


def _registration_response(registration) -> OutboundWebhookRegistrationResponse:
    return OutboundWebhookRegistrationResponse(
        id=registration.id,
        task_id=registration.task_id,
        session_id=registration.session_id,
        target_url=registration.target_url,
        status=registration.status,
        description=registration.description,
        signing_secret_prefix=registration.signing_secret_prefix,
        last_attempt_at=registration.last_attempt_at,
        last_success_at=registration.last_success_at,
        last_failure_at=registration.last_failure_at,
        last_error_message=registration.last_error_message,
        failure_count=registration.failure_count,
        last_delivered_sequence=registration.last_delivered_sequence,
        created_at=registration.created_at,
        updated_at=registration.updated_at,
    )


def _delivery_response(delivery) -> OutboundWebhookDeliveryResponse:
    return OutboundWebhookDeliveryResponse(
        id=delivery.id,
        registration_id=delivery.registration_id,
        task_id=delivery.task_id,
        session_id=delivery.session_id,
        event_id=delivery.event_id,
        event_sequence=delivery.event_sequence,
        event_type=delivery.event_type,
        status=delivery.status,
        attempt_count=delivery.attempt_count,
        next_attempt_at=delivery.next_attempt_at,
        last_attempt_at=delivery.last_attempt_at,
        last_success_at=delivery.last_success_at,
        last_failure_at=delivery.last_failure_at,
        last_response_status=delivery.last_response_status,
        last_error_message=delivery.last_error_message,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
    )


@router.post(
    "/{task_id}/webhooks",
    response_model=OutboundWebhookEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_outbound_webhook(
    task_id: str,
    payload: OutboundWebhookCreateRequest,
    service: Annotated[OutboundWebhookService, Depends(get_outbound_webhook_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
) -> OutboundWebhookEnvelope:
    authz_service.require_operator_action(actor_identity, action="manage_outbound_webhook")
    try:
        registration, secret = await service.create_registration(
            task_id=task_id,
            target_url=payload.target_url,
            signing_secret=payload.signing_secret,
            description=payload.description,
            actor_identity=actor_identity,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OutboundWebhookEnvelope(
        webhook=_registration_response(registration),
        signing_secret=secret,
    )


@router.get("/{task_id}/webhooks", response_model=OutboundWebhookListEnvelope)
async def list_outbound_webhooks(
    task_id: str,
    service: Annotated[OutboundWebhookService, Depends(get_outbound_webhook_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
) -> OutboundWebhookListEnvelope:
    authz_service.require_operator_action(actor_identity, action="list_outbound_webhooks")
    try:
        registrations = await service.list_registrations(task_id=task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OutboundWebhookListEnvelope(
        webhooks=[_registration_response(item) for item in registrations]
    )


@router.get("/{task_id}/webhook-deliveries", response_model=OutboundWebhookDeliveryListEnvelope)
async def list_outbound_webhook_deliveries(
    task_id: str,
    service: Annotated[OutboundWebhookService, Depends(get_outbound_webhook_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
) -> OutboundWebhookDeliveryListEnvelope:
    authz_service.require_operator_action(actor_identity, action="list_outbound_webhooks")
    try:
        deliveries = await service.list_deliveries(task_id=task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OutboundWebhookDeliveryListEnvelope(
        deliveries=[_delivery_response(item) for item in deliveries]
    )


@router.post("/webhooks/{registration_id}/disable", response_model=OutboundWebhookEnvelope)
async def disable_outbound_webhook(
    registration_id: str,
    service: Annotated[OutboundWebhookService, Depends(get_outbound_webhook_service)],
    actor_identity: Annotated[ActorIdentity, Depends(get_operator_actor_identity)],
    authz_service: Annotated[AuthzService, Depends(get_authz_service)],
    payload: OutboundWebhookDisableRequest | None = None,
) -> OutboundWebhookEnvelope:
    authz_service.require_operator_action(actor_identity, action="manage_outbound_webhook")
    try:
        registration = await service.disable_registration(
            registration_id,
            reason=payload.reason if payload is not None else None,
            actor_identity=actor_identity,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OutboundWebhookEnvelope(webhook=_registration_response(registration))
