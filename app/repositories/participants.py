"""Session participant repository."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import sqlite3

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class SessionParticipantRecord:
    """Session participant row."""

    id: str
    session_id: str
    agent_id: str
    runtime_id: str | None
    is_lead: int
    read_scope: str
    write_scope: str
    participant_status: str
    joined_at: str | None
    left_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SessionParticipantRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            agent_id=row["agent_id"],
            runtime_id=row["runtime_id"],
            is_lead=row["is_lead"],
            read_scope=row["read_scope"],
            write_scope=row["write_scope"],
            participant_status=row["participant_status"],
            joined_at=row["joined_at"],
            left_at=row["left_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class ParticipantRepository(SQLiteRepositoryBase):
    """CRUD access for session participants."""

    async def create(self, participant: SessionParticipantRecord) -> SessionParticipantRecord:
        return await self._run(lambda connection: self._create_sync(connection, participant))

    async def get(self, participant_id: str) -> SessionParticipantRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, participant_id))

    async def get_by_session_and_agent(
        self,
        session_id: str,
        agent_id: str,
    ) -> SessionParticipantRecord | None:
        return await self._run(
            lambda connection: self._get_by_session_and_agent_sync(connection, session_id, agent_id)
        )

    async def list_by_session(self, session_id: str) -> list[SessionParticipantRecord]:
        return await self._run(lambda connection: self._list_by_session_sync(connection, session_id))

    async def update(self, participant: SessionParticipantRecord) -> SessionParticipantRecord:
        return await self._run(lambda connection: self._update_sync(connection, participant))

    async def delete(self, participant_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, participant_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        participant: SessionParticipantRecord,
    ) -> SessionParticipantRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO session_participants (
                    id, session_id, agent_id, runtime_id, is_lead,
                    read_scope, write_scope, participant_status, joined_at,
                    left_at, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :agent_id, :runtime_id, :is_lead,
                    :read_scope, :write_scope, :participant_status, :joined_at,
                    :left_at, :created_at, :updated_at
                )
                """,
                asdict(participant),
            )
        return participant

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        participant_id: str,
    ) -> SessionParticipantRecord | None:
        row = connection.execute(
            "SELECT * FROM session_participants WHERE id = ?",
            (participant_id,),
        ).fetchone()
        return SessionParticipantRecord.from_row(row) if row else None

    def _get_by_session_and_agent_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        agent_id: str,
    ) -> SessionParticipantRecord | None:
        row = connection.execute(
            """
            SELECT * FROM session_participants
            WHERE session_id = ? AND agent_id = ?
            """,
            (session_id, agent_id),
        ).fetchone()
        return SessionParticipantRecord.from_row(row) if row else None

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[SessionParticipantRecord]:
        rows = connection.execute(
            """
            SELECT * FROM session_participants
            WHERE session_id = ?
            ORDER BY created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [SessionParticipantRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        participant: SessionParticipantRecord,
    ) -> SessionParticipantRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE session_participants SET
                    session_id = :session_id,
                    agent_id = :agent_id,
                    runtime_id = :runtime_id,
                    is_lead = :is_lead,
                    read_scope = :read_scope,
                    write_scope = :write_scope,
                    participant_status = :participant_status,
                    joined_at = :joined_at,
                    left_at = :left_at,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(participant),
            )
        if result.rowcount == 0:
            raise LookupError(f"Participant not found: {participant.id}")
        return participant

    def _delete_sync(self, connection: sqlite3.Connection, participant_id: str) -> bool:
        with connection:
            result = connection.execute(
                "DELETE FROM session_participants WHERE id = ?",
                (participant_id,),
            )
        return result.rowcount > 0
