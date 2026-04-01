"""Public A2A task subscription repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class PublicTaskSubscriptionRecord:
    """Public task subscription row."""

    id: str
    task_id: str
    session_id: str
    cursor_sequence: int
    delivery_mode: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PublicTaskSubscriptionRecord":
        return cls(
            id=row["id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            cursor_sequence=row["cursor_sequence"],
            delivery_mode=row["delivery_mode"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class PublicTaskSubscriptionRepository(SQLiteRepositoryBase):
    """CRUD access for public task subscriptions."""

    async def create(
        self,
        subscription: PublicTaskSubscriptionRecord,
    ) -> PublicTaskSubscriptionRecord:
        return await self._run(lambda connection: self._create_sync(connection, subscription))

    async def get(self, subscription_id: str) -> PublicTaskSubscriptionRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, subscription_id))

    async def list(self) -> list[PublicTaskSubscriptionRecord]:
        return await self._run(self._list_sync)

    async def list_by_task(self, task_id: str) -> list[PublicTaskSubscriptionRecord]:
        return await self._run(
            lambda connection: self._list_by_task_sync(connection, task_id)
        )

    async def update(
        self,
        subscription: PublicTaskSubscriptionRecord,
    ) -> PublicTaskSubscriptionRecord:
        return await self._run(lambda connection: self._update_sync(connection, subscription))

    async def delete(self, subscription_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, subscription_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        subscription: PublicTaskSubscriptionRecord,
    ) -> PublicTaskSubscriptionRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO a2a_public_subscriptions (
                    id, task_id, session_id, cursor_sequence, delivery_mode,
                    created_at, updated_at
                ) VALUES (
                    :id, :task_id, :session_id, :cursor_sequence, :delivery_mode,
                    :created_at, :updated_at
                )
                """,
                asdict(subscription),
            )
        return subscription

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        subscription_id: str,
    ) -> PublicTaskSubscriptionRecord | None:
        row = connection.execute(
            "SELECT * FROM a2a_public_subscriptions WHERE id = ?",
            (subscription_id,),
        ).fetchone()
        return PublicTaskSubscriptionRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[PublicTaskSubscriptionRecord]:
        rows = connection.execute(
            "SELECT * FROM a2a_public_subscriptions ORDER BY created_at, id"
        ).fetchall()
        return [PublicTaskSubscriptionRecord.from_row(row) for row in rows]

    def _list_by_task_sync(
        self,
        connection: sqlite3.Connection,
        task_id: str,
    ) -> list[PublicTaskSubscriptionRecord]:
        rows = connection.execute(
            """
            SELECT * FROM a2a_public_subscriptions
            WHERE task_id = ?
            ORDER BY created_at, id
            """,
            (task_id,),
        ).fetchall()
        return [PublicTaskSubscriptionRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        subscription: PublicTaskSubscriptionRecord,
    ) -> PublicTaskSubscriptionRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE a2a_public_subscriptions SET
                    task_id = :task_id,
                    session_id = :session_id,
                    cursor_sequence = :cursor_sequence,
                    delivery_mode = :delivery_mode,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(subscription),
            )
        if result.rowcount == 0:
            raise LookupError(f"Public subscription not found: {subscription.id}")
        return subscription

    def _delete_sync(self, connection: sqlite3.Connection, subscription_id: str) -> bool:
        with connection:
            result = connection.execute(
                "DELETE FROM a2a_public_subscriptions WHERE id = ?",
                (subscription_id,),
            )
        return result.rowcount > 0
