"""Session repository."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import sqlite3

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """Session row."""

    id: str
    title: str
    goal: str | None
    status: str
    lead_agent_id: str | None
    active_phase_id: str | None
    loop_guard_status: str
    loop_guard_reason: str | None
    last_message_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SessionRecord":
        return cls(
            id=row["id"],
            title=row["title"],
            goal=row["goal"],
            status=row["status"],
            lead_agent_id=row["lead_agent_id"],
            active_phase_id=row["active_phase_id"],
            loop_guard_status=row["loop_guard_status"],
            loop_guard_reason=row["loop_guard_reason"],
            last_message_at=row["last_message_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class SessionRepository(SQLiteRepositoryBase):
    """CRUD access for sessions."""

    async def create(self, session: SessionRecord) -> SessionRecord:
        return await self._run(lambda connection: self._create_sync(connection, session))

    async def get(self, session_id: str) -> SessionRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, session_id))

    async def list(self) -> list[SessionRecord]:
        return await self._run(self._list_sync)

    async def update(self, session: SessionRecord) -> SessionRecord:
        return await self._run(lambda connection: self._update_sync(connection, session))

    async def delete(self, session_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, session_id))

    def _create_sync(self, connection: sqlite3.Connection, session: SessionRecord) -> SessionRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id, title, goal, status, lead_agent_id, active_phase_id,
                    loop_guard_status, loop_guard_reason, last_message_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :title, :goal, :status, :lead_agent_id, :active_phase_id,
                    :loop_guard_status, :loop_guard_reason, :last_message_at,
                    :created_at, :updated_at
                )
                """,
                asdict(session),
            )
        return session

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> SessionRecord | None:
        row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return SessionRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[SessionRecord]:
        rows = connection.execute("SELECT * FROM sessions ORDER BY created_at, id").fetchall()
        return [SessionRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, session: SessionRecord) -> SessionRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE sessions SET
                    title = :title,
                    goal = :goal,
                    status = :status,
                    lead_agent_id = :lead_agent_id,
                    active_phase_id = :active_phase_id,
                    loop_guard_status = :loop_guard_status,
                    loop_guard_reason = :loop_guard_reason,
                    last_message_at = :last_message_at,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(session),
            )
        if result.rowcount == 0:
            raise LookupError(f"Session not found: {session.id}")
        return session

    def _delete_sync(self, connection: sqlite3.Connection, session_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return result.rowcount > 0
