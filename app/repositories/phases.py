"""Phase repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class PhaseRecord:
    """Phase row."""

    id: str
    session_id: str
    phase_key: str
    title: str
    description: str | None
    relay_template_key: str
    default_channel_key: str
    sort_order: int
    is_default: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PhaseRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            phase_key=row["phase_key"],
            title=row["title"],
            description=row["description"],
            relay_template_key=row["relay_template_key"],
            default_channel_key=row["default_channel_key"],
            sort_order=row["sort_order"],
            is_default=row["is_default"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class PhaseRepository(SQLiteRepositoryBase):
    """CRUD access for session phases."""

    async def create(self, phase: PhaseRecord) -> PhaseRecord:
        return await self._run(lambda connection: self._create_sync(connection, phase))

    async def get(self, phase_id: str) -> PhaseRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, phase_id))

    async def get_by_session_and_key(
        self,
        session_id: str,
        phase_key: str,
    ) -> PhaseRecord | None:
        return await self._run(
            lambda connection: self._get_by_session_and_key_sync(connection, session_id, phase_key)
        )

    async def list(self) -> list[PhaseRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[PhaseRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def update(self, phase: PhaseRecord) -> PhaseRecord:
        return await self._run(lambda connection: self._update_sync(connection, phase))

    async def delete(self, phase_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, phase_id))

    def _create_sync(self, connection: sqlite3.Connection, phase: PhaseRecord) -> PhaseRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO phases (
                    id, session_id, phase_key, title, description, relay_template_key,
                    default_channel_key, sort_order, is_default, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :phase_key, :title, :description, :relay_template_key,
                    :default_channel_key, :sort_order, :is_default, :created_at, :updated_at
                )
                """,
                asdict(phase),
            )
        return phase

    def _get_sync(self, connection: sqlite3.Connection, phase_id: str) -> PhaseRecord | None:
        row = connection.execute("SELECT * FROM phases WHERE id = ?", (phase_id,)).fetchone()
        return PhaseRecord.from_row(row) if row else None

    def _get_by_session_and_key_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        phase_key: str,
    ) -> PhaseRecord | None:
        row = connection.execute(
            """
            SELECT * FROM phases
            WHERE session_id = ? AND phase_key = ?
            """,
            (session_id, phase_key),
        ).fetchone()
        return PhaseRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[PhaseRecord]:
        rows = connection.execute(
            "SELECT * FROM phases ORDER BY session_id, sort_order, id"
        ).fetchall()
        return [PhaseRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[PhaseRecord]:
        rows = connection.execute(
            """
            SELECT * FROM phases
            WHERE session_id = ?
            ORDER BY sort_order, created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [PhaseRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, phase: PhaseRecord) -> PhaseRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE phases SET
                    session_id = :session_id,
                    phase_key = :phase_key,
                    title = :title,
                    description = :description,
                    relay_template_key = :relay_template_key,
                    default_channel_key = :default_channel_key,
                    sort_order = :sort_order,
                    is_default = :is_default,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(phase),
            )
        if result.rowcount == 0:
            raise LookupError(f"Phase not found: {phase.id}")
        return phase

    def _delete_sync(self, connection: sqlite3.Connection, phase_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM phases WHERE id = ?", (phase_id,))
        return result.rowcount > 0
