"""Presence repository."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import sqlite3

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class PresenceHeartbeatRecord:
    """Presence heartbeat row."""

    id: str
    agent_id: str
    runtime_id: str | None
    presence: str
    heartbeat_at: str
    details_json: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PresenceHeartbeatRecord":
        return cls(
            id=row["id"],
            agent_id=row["agent_id"],
            runtime_id=row["runtime_id"],
            presence=row["presence"],
            heartbeat_at=row["heartbeat_at"],
            details_json=row["details_json"],
            created_at=row["created_at"],
        )


class PresenceRepository(SQLiteRepositoryBase):
    """CRUD access for presence heartbeats."""

    async def create(self, heartbeat: PresenceHeartbeatRecord) -> PresenceHeartbeatRecord:
        return await self._run(lambda connection: self._create_sync(connection, heartbeat))

    async def get(self, heartbeat_id: str) -> PresenceHeartbeatRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, heartbeat_id))

    async def list(self) -> list[PresenceHeartbeatRecord]:
        return await self._run(self._list_sync)

    async def list_by_agent(self, agent_id: str) -> list[PresenceHeartbeatRecord]:
        return await self._run(lambda connection: self._list_by_agent_sync(connection, agent_id))

    async def list_by_runtime(self, runtime_id: str) -> list[PresenceHeartbeatRecord]:
        return await self._run(lambda connection: self._list_by_runtime_sync(connection, runtime_id))

    async def update(self, heartbeat: PresenceHeartbeatRecord) -> PresenceHeartbeatRecord:
        return await self._run(lambda connection: self._update_sync(connection, heartbeat))

    async def delete(self, heartbeat_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, heartbeat_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        heartbeat: PresenceHeartbeatRecord,
    ) -> PresenceHeartbeatRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO presence_heartbeats (
                    id, agent_id, runtime_id, presence, heartbeat_at,
                    details_json, created_at
                ) VALUES (
                    :id, :agent_id, :runtime_id, :presence, :heartbeat_at,
                    :details_json, :created_at
                )
                """,
                asdict(heartbeat),
            )
        return heartbeat

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        heartbeat_id: str,
    ) -> PresenceHeartbeatRecord | None:
        row = connection.execute(
            "SELECT * FROM presence_heartbeats WHERE id = ?",
            (heartbeat_id,),
        ).fetchone()
        return PresenceHeartbeatRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[PresenceHeartbeatRecord]:
        rows = connection.execute("SELECT * FROM presence_heartbeats ORDER BY created_at, id").fetchall()
        return [PresenceHeartbeatRecord.from_row(row) for row in rows]

    def _list_by_agent_sync(
        self,
        connection: sqlite3.Connection,
        agent_id: str,
    ) -> list[PresenceHeartbeatRecord]:
        rows = connection.execute(
            "SELECT * FROM presence_heartbeats WHERE agent_id = ? ORDER BY heartbeat_at, id",
            (agent_id,),
        ).fetchall()
        return [PresenceHeartbeatRecord.from_row(row) for row in rows]

    def _list_by_runtime_sync(
        self,
        connection: sqlite3.Connection,
        runtime_id: str,
    ) -> list[PresenceHeartbeatRecord]:
        rows = connection.execute(
            "SELECT * FROM presence_heartbeats WHERE runtime_id = ? ORDER BY heartbeat_at, id",
            (runtime_id,),
        ).fetchall()
        return [PresenceHeartbeatRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        heartbeat: PresenceHeartbeatRecord,
    ) -> PresenceHeartbeatRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE presence_heartbeats SET
                    agent_id = :agent_id,
                    runtime_id = :runtime_id,
                    presence = :presence,
                    heartbeat_at = :heartbeat_at,
                    details_json = :details_json,
                    created_at = :created_at
                WHERE id = :id
                """,
                asdict(heartbeat),
            )
        if result.rowcount == 0:
            raise LookupError(f"Presence heartbeat not found: {heartbeat.id}")
        return heartbeat

    def _delete_sync(self, connection: sqlite3.Connection, heartbeat_id: str) -> bool:
        with connection:
            result = connection.execute(
                "DELETE FROM presence_heartbeats WHERE id = ?",
                (heartbeat_id,),
            )
        return result.rowcount > 0
