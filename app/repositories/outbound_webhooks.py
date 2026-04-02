"""Outbound webhook persistence repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class OutboundWebhookRegistrationRecord:
    """Outbound webhook registration row."""

    id: str
    task_id: str
    session_id: str
    target_url: str
    signing_secret: str
    signing_secret_prefix: str
    status: str
    description: str | None
    last_attempt_at: str | None
    last_success_at: str | None
    last_failure_at: str | None
    last_error_message: str | None
    failure_count: int
    last_delivered_sequence: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "OutboundWebhookRegistrationRecord":
        return cls(
            id=row["id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            target_url=row["target_url"],
            signing_secret=row["signing_secret"],
            signing_secret_prefix=row["signing_secret_prefix"],
            status=row["status"],
            description=row["description"],
            last_attempt_at=row["last_attempt_at"],
            last_success_at=row["last_success_at"],
            last_failure_at=row["last_failure_at"],
            last_error_message=row["last_error_message"],
            failure_count=row["failure_count"],
            last_delivered_sequence=row["last_delivered_sequence"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True, slots=True)
class OutboundWebhookDeliveryRecord:
    """Outbound webhook delivery row."""

    id: str
    registration_id: str
    task_id: str
    session_id: str
    event_id: str
    event_sequence: int
    event_type: str
    payload_json: str
    status: str
    attempt_count: int
    next_attempt_at: str
    last_attempt_at: str | None
    last_success_at: str | None
    last_failure_at: str | None
    last_response_status: int | None
    last_error_message: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "OutboundWebhookDeliveryRecord":
        return cls(
            id=row["id"],
            registration_id=row["registration_id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            event_id=row["event_id"],
            event_sequence=row["event_sequence"],
            event_type=row["event_type"],
            payload_json=row["payload_json"],
            status=row["status"],
            attempt_count=row["attempt_count"],
            next_attempt_at=row["next_attempt_at"],
            last_attempt_at=row["last_attempt_at"],
            last_success_at=row["last_success_at"],
            last_failure_at=row["last_failure_at"],
            last_response_status=row["last_response_status"],
            last_error_message=row["last_error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class OutboundWebhookRegistrationRepository(SQLiteRepositoryBase):
    """CRUD access for outbound webhook registrations."""

    async def create(
        self,
        registration: OutboundWebhookRegistrationRecord,
    ) -> OutboundWebhookRegistrationRecord:
        return await self._run(lambda connection: self._create_sync(connection, registration))

    async def get(self, registration_id: str) -> OutboundWebhookRegistrationRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, registration_id))

    async def list(self) -> list[OutboundWebhookRegistrationRecord]:
        return await self._run(self._list_sync)

    async def list_by_task(self, task_id: str) -> list[OutboundWebhookRegistrationRecord]:
        return await self._run(lambda connection: self._list_by_task_sync(connection, task_id))

    async def update(
        self,
        registration: OutboundWebhookRegistrationRecord,
    ) -> OutboundWebhookRegistrationRecord:
        return await self._run(lambda connection: self._update_sync(connection, registration))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        registration: OutboundWebhookRegistrationRecord,
    ) -> OutboundWebhookRegistrationRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO outbound_webhook_registrations (
                    id, task_id, session_id, target_url, signing_secret,
                    signing_secret_prefix, status, description, last_attempt_at,
                    last_success_at, last_failure_at, last_error_message, failure_count,
                    last_delivered_sequence, created_at, updated_at
                ) VALUES (
                    :id, :task_id, :session_id, :target_url, :signing_secret,
                    :signing_secret_prefix, :status, :description, :last_attempt_at,
                    :last_success_at, :last_failure_at, :last_error_message, :failure_count,
                    :last_delivered_sequence, :created_at, :updated_at
                )
                """,
                asdict(registration),
            )
        return registration

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        registration_id: str,
    ) -> OutboundWebhookRegistrationRecord | None:
        row = connection.execute(
            "SELECT * FROM outbound_webhook_registrations WHERE id = ?",
            (registration_id,),
        ).fetchone()
        return OutboundWebhookRegistrationRecord.from_row(row) if row else None

    def _list_sync(
        self,
        connection: sqlite3.Connection,
    ) -> list[OutboundWebhookRegistrationRecord]:
        rows = connection.execute(
            "SELECT * FROM outbound_webhook_registrations ORDER BY created_at, id"
        ).fetchall()
        return [OutboundWebhookRegistrationRecord.from_row(row) for row in rows]

    def _list_by_task_sync(
        self,
        connection: sqlite3.Connection,
        task_id: str,
    ) -> list[OutboundWebhookRegistrationRecord]:
        rows = connection.execute(
            """
            SELECT * FROM outbound_webhook_registrations
            WHERE task_id = ?
            ORDER BY created_at, id
            """,
            (task_id,),
        ).fetchall()
        return [OutboundWebhookRegistrationRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        registration: OutboundWebhookRegistrationRecord,
    ) -> OutboundWebhookRegistrationRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE outbound_webhook_registrations SET
                    task_id = :task_id,
                    session_id = :session_id,
                    target_url = :target_url,
                    signing_secret = :signing_secret,
                    signing_secret_prefix = :signing_secret_prefix,
                    status = :status,
                    description = :description,
                    last_attempt_at = :last_attempt_at,
                    last_success_at = :last_success_at,
                    last_failure_at = :last_failure_at,
                    last_error_message = :last_error_message,
                    failure_count = :failure_count,
                    last_delivered_sequence = :last_delivered_sequence,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(registration),
            )
        if result.rowcount == 0:
            raise LookupError(f"Outbound webhook registration not found: {registration.id}")
        return registration


class OutboundWebhookDeliveryRepository(SQLiteRepositoryBase):
    """CRUD access for outbound webhook deliveries."""

    async def create(
        self,
        delivery: OutboundWebhookDeliveryRecord,
    ) -> OutboundWebhookDeliveryRecord:
        return await self._run(lambda connection: self._create_sync(connection, delivery))

    async def get(self, delivery_id: str) -> OutboundWebhookDeliveryRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, delivery_id))

    async def list(self) -> list[OutboundWebhookDeliveryRecord]:
        return await self._run(self._list_sync)

    async def list_by_task(self, task_id: str) -> list[OutboundWebhookDeliveryRecord]:
        return await self._run(lambda connection: self._list_by_task_sync(connection, task_id))

    async def list_pending(self) -> list[OutboundWebhookDeliveryRecord]:
        return await self._run(self._list_pending_sync)

    async def list_due(
        self,
        now: str,
        *,
        limit: int = 100,
    ) -> list[OutboundWebhookDeliveryRecord]:
        return await self._run(lambda connection: self._list_due_sync(connection, now, limit))

    async def update(
        self,
        delivery: OutboundWebhookDeliveryRecord,
    ) -> OutboundWebhookDeliveryRecord:
        return await self._run(lambda connection: self._update_sync(connection, delivery))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        delivery: OutboundWebhookDeliveryRecord,
    ) -> OutboundWebhookDeliveryRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO outbound_webhook_deliveries (
                    id, registration_id, task_id, session_id, event_id, event_sequence,
                    event_type, payload_json, status, attempt_count, next_attempt_at,
                    last_attempt_at, last_success_at, last_failure_at, last_response_status,
                    last_error_message, created_at, updated_at
                ) VALUES (
                    :id, :registration_id, :task_id, :session_id, :event_id, :event_sequence,
                    :event_type, :payload_json, :status, :attempt_count, :next_attempt_at,
                    :last_attempt_at, :last_success_at, :last_failure_at, :last_response_status,
                    :last_error_message, :created_at, :updated_at
                )
                """,
                asdict(delivery),
            )
        return delivery

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        delivery_id: str,
    ) -> OutboundWebhookDeliveryRecord | None:
        row = connection.execute(
            "SELECT * FROM outbound_webhook_deliveries WHERE id = ?",
            (delivery_id,),
        ).fetchone()
        return OutboundWebhookDeliveryRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[OutboundWebhookDeliveryRecord]:
        rows = connection.execute(
            "SELECT * FROM outbound_webhook_deliveries ORDER BY created_at, id"
        ).fetchall()
        return [OutboundWebhookDeliveryRecord.from_row(row) for row in rows]

    def _list_by_task_sync(
        self,
        connection: sqlite3.Connection,
        task_id: str,
    ) -> list[OutboundWebhookDeliveryRecord]:
        rows = connection.execute(
            """
            SELECT * FROM outbound_webhook_deliveries
            WHERE task_id = ?
            ORDER BY event_sequence, created_at, id
            """,
            (task_id,),
        ).fetchall()
        return [OutboundWebhookDeliveryRecord.from_row(row) for row in rows]

    def _list_due_sync(
        self,
        connection: sqlite3.Connection,
        now: str,
        limit: int,
    ) -> list[OutboundWebhookDeliveryRecord]:
        rows = connection.execute(
            """
            SELECT * FROM outbound_webhook_deliveries
            WHERE status IN ('pending', 'retrying')
              AND next_attempt_at <= ?
            ORDER BY event_sequence, created_at, id
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        return [OutboundWebhookDeliveryRecord.from_row(row) for row in rows]

    def _list_pending_sync(
        self,
        connection: sqlite3.Connection,
    ) -> list[OutboundWebhookDeliveryRecord]:
        rows = connection.execute(
            """
            SELECT * FROM outbound_webhook_deliveries
            WHERE status IN ('pending', 'retrying')
            ORDER BY registration_id, event_sequence, created_at, id
            """
        ).fetchall()
        return [OutboundWebhookDeliveryRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        delivery: OutboundWebhookDeliveryRecord,
    ) -> OutboundWebhookDeliveryRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE outbound_webhook_deliveries SET
                    registration_id = :registration_id,
                    task_id = :task_id,
                    session_id = :session_id,
                    event_id = :event_id,
                    event_sequence = :event_sequence,
                    event_type = :event_type,
                    payload_json = :payload_json,
                    status = :status,
                    attempt_count = :attempt_count,
                    next_attempt_at = :next_attempt_at,
                    last_attempt_at = :last_attempt_at,
                    last_success_at = :last_success_at,
                    last_failure_at = :last_failure_at,
                    last_response_status = :last_response_status,
                    last_error_message = :last_error_message,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(delivery),
            )
        if result.rowcount == 0:
            raise LookupError(f"Outbound webhook delivery not found: {delivery.id}")
        return delivery
