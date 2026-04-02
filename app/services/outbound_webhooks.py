"""Managed outbound webhook delivery service."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from app.core.errors import NotFoundError
from app.core.telemetry import get_telemetry_service
from app.models.api.a2a_events import A2APublicTaskEventResponse
from app.repositories.a2a_tasks import A2ATaskRepository
from app.repositories.outbound_webhooks import (
    OutboundWebhookDeliveryRecord,
    OutboundWebhookDeliveryRepository,
    OutboundWebhookRegistrationRecord,
    OutboundWebhookRegistrationRepository,
)
from app.repositories.session_events import SessionEventRepository
from app.services.authz_service import ActorIdentity
from app.services.session_events import record_session_event

_ACTIVE_STATUS = "active"
_DISABLED_STATUS = "disabled"
_DELIVERED_STATUS = "delivered"
_FAILED_STATUS = "failed"
_PENDING_STATUSES = {"pending", "retrying"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized.removesuffix("Z") + "+00:00"
    return datetime.fromisoformat(normalized)


def _json_payload(event: A2APublicTaskEventResponse) -> str:
    return json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _sign_payload(secret: str, payload_json: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


@dataclass(frozen=True, slots=True)
class OutboundDeliverySweepResult:
    """Summary for one outbound delivery sweep."""

    attempted: int
    delivered: int
    failed: int
    retried: int
    completed_at: str


class OutboundWebhookService:
    """Manage outbound webhook registrations and durable deliveries."""

    def __init__(
        self,
        *,
        task_repository: A2ATaskRepository,
        registration_repository: OutboundWebhookRegistrationRepository,
        delivery_repository: OutboundWebhookDeliveryRepository,
        session_event_repository: SessionEventRepository | None = None,
        request_timeout_seconds: float = 5.0,
        max_attempts: int = 3,
        retry_backoff_seconds: float = 5.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.task_repository = task_repository
        self.registration_repository = registration_repository
        self.delivery_repository = delivery_repository
        self.session_event_repository = session_event_repository
        self.request_timeout_seconds = request_timeout_seconds
        self.max_attempts = max_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self._http_client = http_client

    async def create_registration(
        self,
        *,
        task_id: str,
        target_url: str,
        signing_secret: str | None = None,
        description: str | None = None,
        actor_identity: ActorIdentity | None = None,
    ) -> tuple[OutboundWebhookRegistrationRecord, str]:
        """Create a managed webhook registration for a public task."""
        task = await self.task_repository.get(task_id)
        if task is None:
            raise NotFoundError(f"Public task not found: {task_id}")
        normalized_url = self._validate_target_url(target_url)
        secret_value = signing_secret.strip() if signing_secret is not None else ""
        if not secret_value:
            secret_value = secrets.token_urlsafe(24)
        now = _utc_now()
        registration = OutboundWebhookRegistrationRecord(
            id=f"owr_{uuid4().hex}",
            task_id=task_id,
            session_id=task.session_id,
            target_url=normalized_url,
            signing_secret=secret_value,
            signing_secret_prefix=secret_value[:8],
            status=_ACTIVE_STATUS,
            description=(
                description.strip() if description is not None and description.strip() else None
            ),
            last_attempt_at=None,
            last_success_at=None,
            last_failure_at=None,
            last_error_message=None,
            failure_count=0,
            last_delivered_sequence=0,
            created_at=now,
            updated_at=now,
        )
        saved = await self.registration_repository.create(registration)
        if self.session_event_repository is not None:
            await record_session_event(
                self.session_event_repository,
                session_id=task.session_id,
                event_type="outbound.webhook.created",
                actor_type=actor_identity.actor_role if actor_identity is not None else "operator",
                actor_id=actor_identity.actor_id if actor_identity is not None else None,
                payload={
                    "task_id": task_id,
                    "registration_id": saved.id,
                    "target_url": saved.target_url,
                    "actor": actor_identity.as_payload() if actor_identity is not None else None,
                },
            )
        return saved, secret_value

    async def get_registration(
        self,
        registration_id: str,
    ) -> OutboundWebhookRegistrationRecord:
        """Load a registration or raise if missing."""
        registration = await self.registration_repository.get(registration_id)
        if registration is None:
            raise NotFoundError(f"Outbound webhook registration not found: {registration_id}")
        return registration

    async def list_registrations(
        self,
        *,
        task_id: str,
    ) -> list[OutboundWebhookRegistrationRecord]:
        """List registrations for a task."""
        if await self.task_repository.get(task_id) is None:
            raise NotFoundError(f"Public task not found: {task_id}")
        return await self.registration_repository.list_by_task(task_id)

    async def disable_registration(
        self,
        registration_id: str,
        *,
        reason: str | None = None,
        actor_identity: ActorIdentity | None = None,
    ) -> OutboundWebhookRegistrationRecord:
        """Disable a registration so future events are not enqueued."""
        registration = await self.get_registration(registration_id)
        if registration.status == _DISABLED_STATUS:
            return registration
        updated = replace(
            registration,
            status=_DISABLED_STATUS,
            last_error_message=reason or registration.last_error_message,
            updated_at=_utc_now(),
        )
        saved = await self.registration_repository.update(updated)
        if self.session_event_repository is not None:
            await record_session_event(
                self.session_event_repository,
                session_id=saved.session_id,
                event_type="outbound.webhook.disabled",
                actor_type=actor_identity.actor_role if actor_identity is not None else "operator",
                actor_id=actor_identity.actor_id if actor_identity is not None else None,
                payload={
                    "task_id": saved.task_id,
                    "registration_id": saved.id,
                    "reason": reason,
                    "actor": actor_identity.as_payload() if actor_identity is not None else None,
                },
            )
        return saved

    async def list_deliveries(
        self,
        *,
        task_id: str,
    ) -> list[OutboundWebhookDeliveryRecord]:
        """List deliveries for a task."""
        if await self.task_repository.get(task_id) is None:
            raise NotFoundError(f"Public task not found: {task_id}")
        return await self.delivery_repository.list_by_task(task_id)

    async def enqueue_events(
        self,
        *,
        task_id: str,
        session_id: str,
        events: list[A2APublicTaskEventResponse],
    ) -> list[OutboundWebhookDeliveryRecord]:
        """Create durable delivery rows for active registrations on a task."""
        if not events:
            return []
        registrations = await self.registration_repository.list_by_task(task_id)
        active_registrations = [item for item in registrations if item.status == _ACTIVE_STATUS]
        if not active_registrations:
            return []
        existing = await self.delivery_repository.list_by_task(task_id)
        existing_keys = {(item.registration_id, item.event_id) for item in existing}
        created: list[OutboundWebhookDeliveryRecord] = []
        now = _utc_now()
        for registration in active_registrations:
            for event in events:
                key = (registration.id, event.event_id)
                if key in existing_keys:
                    continue
                delivery = OutboundWebhookDeliveryRecord(
                    id=f"owd_{uuid4().hex}",
                    registration_id=registration.id,
                    task_id=task_id,
                    session_id=session_id,
                    event_id=event.event_id,
                    event_sequence=event.sequence,
                    event_type=event.event_type,
                    payload_json=_json_payload(event),
                    status="pending",
                    attempt_count=0,
                    next_attempt_at=now,
                    last_attempt_at=None,
                    last_success_at=None,
                    last_failure_at=None,
                    last_response_status=None,
                    last_error_message=None,
                    created_at=now,
                    updated_at=now,
                )
                saved = await self.delivery_repository.create(delivery)
                existing_keys.add(key)
                created.append(saved)
        return created

    async def dispatch_due_deliveries(
        self,
        *,
        limit: int = 100,
    ) -> OutboundDeliverySweepResult:
        """Dispatch pending or retryable deliveries due as of now."""
        due = await self._list_dispatchable_deliveries(limit=limit)
        return await self._dispatch_deliveries(due)

    async def dispatch_task_deliveries(self, task_id: str) -> OutboundDeliverySweepResult:
        """Dispatch due deliveries scoped to one task."""
        deliveries = await self.delivery_repository.list_by_task(task_id)
        due = self._select_dispatchable_deliveries(deliveries)
        return await self._dispatch_deliveries(due)

    async def _list_dispatchable_deliveries(
        self,
        *,
        limit: int,
    ) -> list[OutboundWebhookDeliveryRecord]:
        pending = await self.delivery_repository.list_pending()
        return self._select_dispatchable_deliveries(pending)[:limit]

    def _select_dispatchable_deliveries(
        self,
        deliveries: list[OutboundWebhookDeliveryRecord],
    ) -> list[OutboundWebhookDeliveryRecord]:
        """Select the oldest due delivery per registration to preserve ordering."""
        now = datetime.now(timezone.utc)
        pending = sorted(
            (item for item in deliveries if item.status in _PENDING_STATUSES),
            key=lambda item: (
                item.registration_id,
                item.event_sequence,
                item.created_at,
                item.id,
            ),
        )
        dispatchable: list[OutboundWebhookDeliveryRecord] = []
        current_registration_id: str | None = None
        for delivery in pending:
            if delivery.registration_id == current_registration_id:
                continue
            current_registration_id = delivery.registration_id
            if _parse_iso_datetime(delivery.next_attempt_at) <= now:
                dispatchable.append(delivery)
        return dispatchable

    async def _dispatch_deliveries(
        self,
        deliveries: list[OutboundWebhookDeliveryRecord],
    ) -> OutboundDeliverySweepResult:
        delivered = 0
        failed = 0
        retried = 0
        for delivery in deliveries:
            result = await self._dispatch_delivery(delivery)
            if result == _DELIVERED_STATUS:
                delivered += 1
            elif result == _FAILED_STATUS:
                failed += 1
            elif result == "retrying":
                retried += 1
        return OutboundDeliverySweepResult(
            attempted=len(deliveries),
            delivered=delivered,
            failed=failed,
            retried=retried,
            completed_at=_utc_now(),
        )

    async def _dispatch_delivery(self, delivery: OutboundWebhookDeliveryRecord) -> str:
        registration = await self.registration_repository.get(delivery.registration_id)
        if registration is None or registration.status != _ACTIVE_STATUS:
            await self._mark_delivery_failed(
                delivery,
                error_message="registration_inactive",
                response_status=None,
            )
            return _FAILED_STATUS
        client = self._http_client or httpx.AsyncClient(timeout=self.request_timeout_seconds)
        close_client = self._http_client is None
        now = _utc_now()
        try:
            response = await client.post(
                registration.target_url,
                content=delivery.payload_json.encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-CCC-Event-Id": delivery.event_id,
                    "X-CCC-Event-Sequence": str(delivery.event_sequence),
                    "X-CCC-Task-Id": delivery.task_id,
                    "X-CCC-Delivery-Attempt": str(delivery.attempt_count + 1),
                    "X-CCC-Signature": _sign_payload(
                        registration.signing_secret,
                        delivery.payload_json,
                    ),
                },
            )
            if 200 <= response.status_code < 300:
                await self._mark_delivery_delivered(
                    delivery,
                    registration=registration,
                    response_status=response.status_code,
                    attempted_at=now,
                )
                return _DELIVERED_STATUS
            return await self._mark_delivery_retry_or_failure(
                delivery,
                registration=registration,
                error_message=f"http_{response.status_code}",
                response_status=response.status_code,
                attempted_at=now,
            )
        except httpx.HTTPError as exc:
            return await self._mark_delivery_retry_or_failure(
                delivery,
                registration=registration,
                error_message=str(exc),
                response_status=None,
                attempted_at=now,
            )
        finally:
            if close_client:
                await client.aclose()

    async def _mark_delivery_delivered(
        self,
        delivery: OutboundWebhookDeliveryRecord,
        *,
        registration: OutboundWebhookRegistrationRecord,
        response_status: int,
        attempted_at: str,
    ) -> None:
        updated_delivery = replace(
            delivery,
            status=_DELIVERED_STATUS,
            attempt_count=delivery.attempt_count + 1,
            next_attempt_at=attempted_at,
            last_attempt_at=attempted_at,
            last_success_at=attempted_at,
            last_response_status=response_status,
            last_error_message=None,
            updated_at=attempted_at,
        )
        updated_registration = replace(
            registration,
            last_attempt_at=attempted_at,
            last_success_at=attempted_at,
            last_error_message=None,
            last_delivered_sequence=max(
                registration.last_delivered_sequence,
                delivery.event_sequence,
            ),
            updated_at=attempted_at,
        )
        await self.delivery_repository.update(updated_delivery)
        await self.registration_repository.update(updated_registration)
        await get_telemetry_service().record_sample(
            "outbound_webhook_delivery",
            metrics={
                "task_id": delivery.task_id,
                "registration_id": registration.id,
                "delivery_id": delivery.id,
                "event_type": delivery.event_type,
                "event_sequence": delivery.event_sequence,
                "status": "delivered",
                "attempt_count": updated_delivery.attempt_count,
            },
        )

    async def _mark_delivery_retry_or_failure(
        self,
        delivery: OutboundWebhookDeliveryRecord,
        *,
        registration: OutboundWebhookRegistrationRecord,
        error_message: str,
        response_status: int | None,
        attempted_at: str,
    ) -> str:
        next_attempt_count = delivery.attempt_count + 1
        should_fail = next_attempt_count >= self.max_attempts
        next_attempt_at = attempted_at
        status = _FAILED_STATUS if should_fail else "retrying"
        if not should_fail:
            retry_at = _parse_iso_datetime(attempted_at) + timedelta(
                seconds=self.retry_backoff_seconds * next_attempt_count
            )
            next_attempt_at = retry_at.isoformat().replace("+00:00", "Z")
        updated_delivery = replace(
            delivery,
            status=status,
            attempt_count=next_attempt_count,
            next_attempt_at=next_attempt_at,
            last_attempt_at=attempted_at,
            last_failure_at=attempted_at,
            last_response_status=response_status,
            last_error_message=error_message,
            updated_at=attempted_at,
        )
        updated_registration = replace(
            registration,
            last_attempt_at=attempted_at,
            last_failure_at=attempted_at,
            last_error_message=error_message,
            failure_count=registration.failure_count + 1,
            updated_at=attempted_at,
        )
        await self.delivery_repository.update(updated_delivery)
        await self.registration_repository.update(updated_registration)
        if self.session_event_repository is not None:
            await record_session_event(
                self.session_event_repository,
                session_id=delivery.session_id,
                event_type="outbound.webhook.delivery_failed",
                actor_type="system",
                actor_id=None,
                payload={
                    "task_id": delivery.task_id,
                    "registration_id": registration.id,
                    "delivery_id": delivery.id,
                    "event_id": delivery.event_id,
                    "event_sequence": delivery.event_sequence,
                    "attempt_count": next_attempt_count,
                    "status": status,
                    "response_status": response_status,
                    "error_message": error_message,
                },
            )
        await get_telemetry_service().record_sample(
            "outbound_webhook_delivery",
            status="error" if should_fail else "ok",
            metrics={
                "task_id": delivery.task_id,
                "registration_id": registration.id,
                "delivery_id": delivery.id,
                "event_type": delivery.event_type,
                "event_sequence": delivery.event_sequence,
                "status": status,
                "attempt_count": next_attempt_count,
                "response_status": response_status,
            },
        )
        return status

    async def _mark_delivery_failed(
        self,
        delivery: OutboundWebhookDeliveryRecord,
        *,
        error_message: str,
        response_status: int | None,
    ) -> None:
        now = _utc_now()
        updated = replace(
            delivery,
            status=_FAILED_STATUS,
            attempt_count=delivery.attempt_count + 1,
            next_attempt_at=now,
            last_attempt_at=now,
            last_failure_at=now,
            last_response_status=response_status,
            last_error_message=error_message,
            updated_at=now,
        )
        await self.delivery_repository.update(updated)

    def _validate_target_url(self, target_url: str) -> str:
        normalized = target_url.strip()
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("target_url must be a valid http or https URL")
        return normalized
