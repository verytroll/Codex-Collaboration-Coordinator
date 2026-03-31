"""Relay edge repository."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import sqlite3

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class RelayEdgeRecord:
    """Relay edge row."""

    id: str
    session_id: str
    source_message_id: str | None
    source_job_id: str | None
    target_agent_id: str
    target_job_id: str | None
    relay_reason: str
    hop_number: int
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RelayEdgeRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            source_message_id=row["source_message_id"],
            source_job_id=row["source_job_id"],
            target_agent_id=row["target_agent_id"],
            target_job_id=row["target_job_id"],
            relay_reason=row["relay_reason"],
            hop_number=row["hop_number"],
            created_at=row["created_at"],
        )


class RelayEdgeRepository(SQLiteRepositoryBase):
    """CRUD access for relay edges."""

    async def create(self, edge: RelayEdgeRecord) -> RelayEdgeRecord:
        return await self._run(lambda connection: self._create_sync(connection, edge))

    async def get(self, edge_id: str) -> RelayEdgeRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, edge_id))

    async def list(self) -> list[RelayEdgeRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[RelayEdgeRecord]:
        return await self._run(lambda connection: self._list_by_session_sync(connection, session_id))

    async def update(self, edge: RelayEdgeRecord) -> RelayEdgeRecord:
        return await self._run(lambda connection: self._update_sync(connection, edge))

    async def delete(self, edge_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, edge_id))

    def _create_sync(self, connection: sqlite3.Connection, edge: RelayEdgeRecord) -> RelayEdgeRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO relay_edges (
                    id, session_id, source_message_id, source_job_id,
                    target_agent_id, target_job_id, relay_reason, hop_number, created_at
                ) VALUES (
                    :id, :session_id, :source_message_id, :source_job_id,
                    :target_agent_id, :target_job_id, :relay_reason, :hop_number, :created_at
                )
                """,
                asdict(edge),
            )
        return edge

    def _get_sync(self, connection: sqlite3.Connection, edge_id: str) -> RelayEdgeRecord | None:
        row = connection.execute("SELECT * FROM relay_edges WHERE id = ?", (edge_id,)).fetchone()
        return RelayEdgeRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[RelayEdgeRecord]:
        rows = connection.execute("SELECT * FROM relay_edges ORDER BY created_at, id").fetchall()
        return [RelayEdgeRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[RelayEdgeRecord]:
        rows = connection.execute(
            "SELECT * FROM relay_edges WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [RelayEdgeRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, edge: RelayEdgeRecord) -> RelayEdgeRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE relay_edges SET
                    session_id = :session_id,
                    source_message_id = :source_message_id,
                    source_job_id = :source_job_id,
                    target_agent_id = :target_agent_id,
                    target_job_id = :target_job_id,
                    relay_reason = :relay_reason,
                    hop_number = :hop_number,
                    created_at = :created_at
                WHERE id = :id
                """,
                asdict(edge),
            )
        if result.rowcount == 0:
            raise LookupError(f"Relay edge not found: {edge.id}")
        return edge

    def _delete_sync(self, connection: sqlite3.Connection, edge_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM relay_edges WHERE id = ?", (edge_id,))
        return result.rowcount > 0
