"""Public A2A task event repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass, replace

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class PublicTaskEventRecord:
    """Public task event row."""

    id: str
    task_id: str
    session_id: str
    sequence: int
    event_type: str
    event_payload_json: str
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PublicTaskEventRecord":
        return cls(
            id=row["id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            sequence=row["sequence"],
            event_type=row["event_type"],
            event_payload_json=row["event_payload_json"],
            created_at=row["created_at"],
        )


class PublicTaskEventRepository(SQLiteRepositoryBase):
    """CRUD access for public task events."""

    async def append(self, event: PublicTaskEventRecord) -> PublicTaskEventRecord:
        return await self._run(lambda connection: self._append_sync(connection, event))

    async def get(self, event_id: str) -> PublicTaskEventRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, event_id))

    async def list(self) -> list[PublicTaskEventRecord]:
        return await self._run(self._list_sync)

    async def list_by_task(self, task_id: str) -> list[PublicTaskEventRecord]:
        return await self._run(lambda connection: self._list_by_task_sync(connection, task_id))

    async def list_since(self, task_id: str, since_sequence: int) -> list[PublicTaskEventRecord]:
        return await self._run(
            lambda connection: self._list_since_sync(connection, task_id, since_sequence)
        )

    def _append_sync(
        self,
        connection: sqlite3.Connection,
        event: PublicTaskEventRecord,
    ) -> PublicTaskEventRecord:
        with connection:
            sequence = self._next_sequence_sync(connection, event.task_id)
            saved_event = replace(event, sequence=sequence)
            connection.execute(
                """
                INSERT INTO a2a_public_events (
                    id, task_id, session_id, sequence, event_type,
                    event_payload_json, created_at
                ) VALUES (
                    :id, :task_id, :session_id, :sequence, :event_type,
                    :event_payload_json, :created_at
                )
                """,
                asdict(saved_event),
            )
        return saved_event

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        event_id: str,
    ) -> PublicTaskEventRecord | None:
        row = connection.execute(
            "SELECT * FROM a2a_public_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        return PublicTaskEventRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[PublicTaskEventRecord]:
        rows = connection.execute(
            "SELECT * FROM a2a_public_events ORDER BY task_id, sequence, id"
        ).fetchall()
        return [PublicTaskEventRecord.from_row(row) for row in rows]

    def _list_by_task_sync(
        self,
        connection: sqlite3.Connection,
        task_id: str,
    ) -> list[PublicTaskEventRecord]:
        rows = connection.execute(
            """
            SELECT * FROM a2a_public_events
            WHERE task_id = ?
            ORDER BY sequence, id
            """,
            (task_id,),
        ).fetchall()
        return [PublicTaskEventRecord.from_row(row) for row in rows]

    def _list_since_sync(
        self,
        connection: sqlite3.Connection,
        task_id: str,
        since_sequence: int,
    ) -> list[PublicTaskEventRecord]:
        rows = connection.execute(
            """
            SELECT * FROM a2a_public_events
            WHERE task_id = ? AND sequence > ?
            ORDER BY sequence, id
            """,
            (task_id, since_sequence),
        ).fetchall()
        return [PublicTaskEventRecord.from_row(row) for row in rows]

    def _next_sequence_sync(self, connection: sqlite3.Connection, task_id: str) -> int:
        row = connection.execute(
            """
            SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence
            FROM a2a_public_events
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        return int(row["next_sequence"]) if row is not None else 1
