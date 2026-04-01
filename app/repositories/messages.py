"""Message and mention repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class MessageRecord:
    """Message row."""

    id: str
    session_id: str
    sender_type: str
    sender_id: str | None
    message_type: str
    content: str
    content_format: str
    reply_to_message_id: str | None
    source_message_id: str | None
    visibility: str
    created_at: str
    updated_at: str
    channel_key: str = "general"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MessageRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            sender_type=row["sender_type"],
            sender_id=row["sender_id"],
            message_type=row["message_type"],
            content=row["content"],
            content_format=row["content_format"],
            reply_to_message_id=row["reply_to_message_id"],
            source_message_id=row["source_message_id"],
            visibility=row["visibility"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            channel_key=row["channel_key"],
        )


@dataclass(frozen=True, slots=True)
class MessageMentionRecord:
    """Message mention row."""

    id: str
    message_id: str
    mentioned_agent_id: str
    mention_text: str
    mention_order: int
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MessageMentionRecord":
        return cls(
            id=row["id"],
            message_id=row["message_id"],
            mentioned_agent_id=row["mentioned_agent_id"],
            mention_text=row["mention_text"],
            mention_order=row["mention_order"],
            created_at=row["created_at"],
        )


class MessageRepository(SQLiteRepositoryBase):
    """CRUD access for messages."""

    async def create(self, message: MessageRecord) -> MessageRecord:
        return await self._run(lambda connection: self._create_sync(connection, message))

    async def get(self, message_id: str) -> MessageRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, message_id))

    async def list(self) -> list[MessageRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[MessageRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def list_by_session_and_channel(
        self,
        session_id: str,
        channel_key: str,
    ) -> list[MessageRecord]:
        return await self._run(
            lambda connection: self._list_by_session_and_channel_sync(
                connection,
                session_id,
                channel_key,
            )
        )

    async def update(self, message: MessageRecord) -> MessageRecord:
        return await self._run(lambda connection: self._update_sync(connection, message))

    async def delete(self, message_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, message_id))

    def _create_sync(self, connection: sqlite3.Connection, message: MessageRecord) -> MessageRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO messages (
                    id, session_id, channel_key, sender_type, sender_id, message_type, content,
                    content_format, reply_to_message_id, source_message_id,
                    visibility, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :channel_key, :sender_type, :sender_id,
                    :message_type, :content, :content_format, :reply_to_message_id,
                    :source_message_id, :visibility, :created_at, :updated_at
                )
                """,
                asdict(message),
            )
        return message

    def _get_sync(self, connection: sqlite3.Connection, message_id: str) -> MessageRecord | None:
        row = connection.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        return MessageRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[MessageRecord]:
        rows = connection.execute("SELECT * FROM messages ORDER BY created_at, id").fetchall()
        return [MessageRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[MessageRecord]:
        rows = connection.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [MessageRecord.from_row(row) for row in rows]

    def _list_by_session_and_channel_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        channel_key: str,
    ) -> list[MessageRecord]:
        rows = connection.execute(
            """
            SELECT * FROM messages
            WHERE session_id = ? AND channel_key = ?
            ORDER BY created_at, id
            """,
            (session_id, channel_key),
        ).fetchall()
        return [MessageRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, message: MessageRecord) -> MessageRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE messages SET
                    session_id = :session_id,
                    channel_key = :channel_key,
                    sender_type = :sender_type,
                    sender_id = :sender_id,
                    message_type = :message_type,
                    content = :content,
                    content_format = :content_format,
                    reply_to_message_id = :reply_to_message_id,
                    source_message_id = :source_message_id,
                    visibility = :visibility,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(message),
            )
        if result.rowcount == 0:
            raise LookupError(f"Message not found: {message.id}")
        return message

    def _delete_sync(self, connection: sqlite3.Connection, message_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        return result.rowcount > 0


class MessageMentionRepository(SQLiteRepositoryBase):
    """CRUD access for message mentions."""

    async def create(self, mention: MessageMentionRecord) -> MessageMentionRecord:
        return await self._run(lambda connection: self._create_sync(connection, mention))

    async def get(self, mention_id: str) -> MessageMentionRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, mention_id))

    async def list(self) -> list[MessageMentionRecord]:
        return await self._run(self._list_sync)

    async def list_by_message(self, message_id: str) -> list[MessageMentionRecord]:
        return await self._run(
            lambda connection: self._list_by_message_sync(connection, message_id)
        )

    async def list_by_mentioned_agent(self, agent_id: str) -> list[MessageMentionRecord]:
        return await self._run(
            lambda connection: self._list_by_mentioned_agent_sync(connection, agent_id)
        )

    async def update(self, mention: MessageMentionRecord) -> MessageMentionRecord:
        return await self._run(lambda connection: self._update_sync(connection, mention))

    async def delete(self, mention_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, mention_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        mention: MessageMentionRecord,
    ) -> MessageMentionRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO message_mentions (
                    id, message_id, mentioned_agent_id, mention_text,
                    mention_order, created_at
                ) VALUES (
                    :id, :message_id, :mentioned_agent_id, :mention_text,
                    :mention_order, :created_at
                )
                """,
                asdict(mention),
            )
        return mention

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        mention_id: str,
    ) -> MessageMentionRecord | None:
        row = connection.execute(
            "SELECT * FROM message_mentions WHERE id = ?",
            (mention_id,),
        ).fetchone()
        return MessageMentionRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[MessageMentionRecord]:
        rows = connection.execute(
            "SELECT * FROM message_mentions ORDER BY created_at, id"
        ).fetchall()
        return [MessageMentionRecord.from_row(row) for row in rows]

    def _list_by_message_sync(
        self,
        connection: sqlite3.Connection,
        message_id: str,
    ) -> list[MessageMentionRecord]:
        rows = connection.execute(
            "SELECT * FROM message_mentions WHERE message_id = ? ORDER BY mention_order, id",
            (message_id,),
        ).fetchall()
        return [MessageMentionRecord.from_row(row) for row in rows]

    def _list_by_mentioned_agent_sync(
        self,
        connection: sqlite3.Connection,
        agent_id: str,
    ) -> list[MessageMentionRecord]:
        rows = connection.execute(
            "SELECT * FROM message_mentions WHERE mentioned_agent_id = ? ORDER BY created_at, id",
            (agent_id,),
        ).fetchall()
        return [MessageMentionRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        mention: MessageMentionRecord,
    ) -> MessageMentionRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE message_mentions SET
                    message_id = :message_id,
                    mentioned_agent_id = :mentioned_agent_id,
                    mention_text = :mention_text,
                    mention_order = :mention_order,
                    created_at = :created_at
                WHERE id = :id
                """,
                asdict(mention),
            )
        if result.rowcount == 0:
            raise LookupError(f"Message mention not found: {mention.id}")
        return mention

    def _delete_sync(self, connection: sqlite3.Connection, mention_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM message_mentions WHERE id = ?", (mention_id,))
        return result.rowcount > 0
