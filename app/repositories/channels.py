"""Session channel repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class SessionChannelRecord:
    """Session channel row."""

    id: str
    session_id: str
    channel_key: str
    display_name: str
    description: str | None
    is_default: bool
    sort_order: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SessionChannelRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            channel_key=row["channel_key"],
            display_name=row["display_name"],
            description=row["description"],
            is_default=bool(row["is_default"]),
            sort_order=row["sort_order"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class SessionChannelRepository(SQLiteRepositoryBase):
    """CRUD access for session channels."""

    async def create(self, channel: SessionChannelRecord) -> SessionChannelRecord:
        return await self._run(lambda connection: self._create_sync(connection, channel))

    async def get(self, channel_id: str) -> SessionChannelRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, channel_id))

    async def get_by_session_and_key(
        self,
        session_id: str,
        channel_key: str,
    ) -> SessionChannelRecord | None:
        return await self._run(
            lambda connection: self._get_by_session_and_key_sync(
                connection, session_id, channel_key
            )
        )

    async def list(self) -> list[SessionChannelRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[SessionChannelRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def update(self, channel: SessionChannelRecord) -> SessionChannelRecord:
        return await self._run(lambda connection: self._update_sync(connection, channel))

    async def delete(self, channel_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, channel_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        channel: SessionChannelRecord,
    ) -> SessionChannelRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO session_channels (
                    id, session_id, channel_key, display_name, description,
                    is_default, sort_order, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :channel_key, :display_name, :description,
                    :is_default, :sort_order, :created_at, :updated_at
                )
                """,
                asdict(channel),
            )
        return channel

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        channel_id: str,
    ) -> SessionChannelRecord | None:
        row = connection.execute(
            "SELECT * FROM session_channels WHERE id = ?",
            (channel_id,),
        ).fetchone()
        return SessionChannelRecord.from_row(row) if row else None

    def _get_by_session_and_key_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        channel_key: str,
    ) -> SessionChannelRecord | None:
        row = connection.execute(
            """
            SELECT * FROM session_channels
            WHERE session_id = ? AND channel_key = ?
            """,
            (session_id, channel_key),
        ).fetchone()
        return SessionChannelRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[SessionChannelRecord]:
        rows = connection.execute(
            "SELECT * FROM session_channels ORDER BY session_id, sort_order, created_at, id"
        ).fetchall()
        return [SessionChannelRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[SessionChannelRecord]:
        rows = connection.execute(
            """
            SELECT * FROM session_channels
            WHERE session_id = ?
            ORDER BY sort_order, created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [SessionChannelRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        channel: SessionChannelRecord,
    ) -> SessionChannelRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE session_channels SET
                    session_id = :session_id,
                    channel_key = :channel_key,
                    display_name = :display_name,
                    description = :description,
                    is_default = :is_default,
                    sort_order = :sort_order,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(channel),
            )
        if result.rowcount == 0:
            raise LookupError(f"Session channel not found: {channel.id}")
        return channel

    def _delete_sync(self, connection: sqlite3.Connection, channel_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM session_channels WHERE id = ?", (channel_id,))
        return result.rowcount > 0
