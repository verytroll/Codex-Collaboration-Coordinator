"""Session event repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class SessionEventRecord:
    """Session event row."""

    id: str
    session_id: str
    event_type: str
    actor_type: str | None
    actor_id: str | None
    event_payload_json: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SessionEventRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            event_type=row["event_type"],
            actor_type=row["actor_type"],
            actor_id=row["actor_id"],
            event_payload_json=row["event_payload_json"],
            created_at=row["created_at"],
        )


class SessionEventRepository(SQLiteRepositoryBase):
    """CRUD access for session events."""

    async def create(self, event: SessionEventRecord) -> SessionEventRecord:
        return await self._run(lambda connection: self._create_sync(connection, event))

    async def get(self, event_id: str) -> SessionEventRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, event_id))

    async def list(self) -> list[SessionEventRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[SessionEventRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def update(self, event: SessionEventRecord) -> SessionEventRecord:
        return await self._run(lambda connection: self._update_sync(connection, event))

    async def delete(self, event_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, event_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        event: SessionEventRecord,
    ) -> SessionEventRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO session_events (
                    id, session_id, event_type, actor_type, actor_id,
                    event_payload_json, created_at
                ) VALUES (
                    :id, :session_id, :event_type, :actor_type, :actor_id,
                    :event_payload_json, :created_at
                )
                """,
                asdict(event),
            )
        return event

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        event_id: str,
    ) -> SessionEventRecord | None:
        row = connection.execute(
            "SELECT * FROM session_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        return SessionEventRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[SessionEventRecord]:
        rows = connection.execute("SELECT * FROM session_events ORDER BY created_at, id").fetchall()
        return [SessionEventRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[SessionEventRecord]:
        rows = connection.execute(
            "SELECT * FROM session_events WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [SessionEventRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        event: SessionEventRecord,
    ) -> SessionEventRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE session_events SET
                    session_id = :session_id,
                    event_type = :event_type,
                    actor_type = :actor_type,
                    actor_id = :actor_id,
                    event_payload_json = :event_payload_json,
                    created_at = :created_at
                WHERE id = :id
                """,
                asdict(event),
            )
        if result.rowcount == 0:
            raise LookupError(f"Session event not found: {event.id}")
        return event

    def _delete_sync(self, connection: sqlite3.Connection, event_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM session_events WHERE id = ?", (event_id,))
        return result.rowcount > 0
