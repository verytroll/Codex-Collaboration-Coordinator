"""Job and job event repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class JobRecord:
    """Job row."""

    id: str
    session_id: str
    assigned_agent_id: str
    runtime_id: str | None
    source_message_id: str | None
    parent_job_id: str | None
    title: str
    instructions: str | None
    status: str
    hop_count: int
    priority: str
    codex_runtime_id: str | None
    codex_thread_id: str | None
    active_turn_id: str | None
    last_known_turn_status: str | None
    result_summary: str | None
    error_code: str | None
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str
    channel_key: str = "general"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "JobRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            assigned_agent_id=row["assigned_agent_id"],
            runtime_id=row["runtime_id"],
            source_message_id=row["source_message_id"],
            parent_job_id=row["parent_job_id"],
            title=row["title"],
            instructions=row["instructions"],
            status=row["status"],
            hop_count=row["hop_count"],
            priority=row["priority"],
            codex_runtime_id=row["codex_runtime_id"],
            codex_thread_id=row["codex_thread_id"],
            active_turn_id=row["active_turn_id"],
            last_known_turn_status=row["last_known_turn_status"],
            result_summary=row["result_summary"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            channel_key=row["channel_key"],
        )


@dataclass(frozen=True, slots=True)
class JobEventRecord:
    """Job event row."""

    id: str
    job_id: str
    session_id: str
    event_type: str
    event_payload_json: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "JobEventRecord":
        return cls(
            id=row["id"],
            job_id=row["job_id"],
            session_id=row["session_id"],
            event_type=row["event_type"],
            event_payload_json=row["event_payload_json"],
            created_at=row["created_at"],
        )


class JobRepository(SQLiteRepositoryBase):
    """CRUD access for jobs."""

    async def create(self, job: JobRecord) -> JobRecord:
        return await self._run(lambda connection: self._create_sync(connection, job))

    async def get(self, job_id: str) -> JobRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, job_id))

    async def list(self) -> list[JobRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[JobRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def list_by_agent(self, agent_id: str) -> list[JobRecord]:
        return await self._run(lambda connection: self._list_by_agent_sync(connection, agent_id))

    async def update(self, job: JobRecord) -> JobRecord:
        return await self._run(lambda connection: self._update_sync(connection, job))

    async def delete(self, job_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, job_id))

    def _create_sync(self, connection: sqlite3.Connection, job: JobRecord) -> JobRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, session_id, channel_key, assigned_agent_id, runtime_id, source_message_id,
                    parent_job_id, title, instructions, status, hop_count, priority,
                    codex_runtime_id, codex_thread_id, active_turn_id,
                    last_known_turn_status, result_summary, error_code, error_message,
                    started_at, completed_at, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :channel_key, :assigned_agent_id, :runtime_id,
                    :source_message_id, :parent_job_id, :title, :instructions, :status,
                    :hop_count, :priority, :codex_runtime_id, :codex_thread_id,
                    :active_turn_id, :last_known_turn_status, :result_summary,
                    :error_code, :error_message, :started_at, :completed_at,
                    :created_at, :updated_at
                )
                """,
                asdict(job),
            )
        return job

    def _get_sync(self, connection: sqlite3.Connection, job_id: str) -> JobRecord | None:
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return JobRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[JobRecord]:
        rows = connection.execute("SELECT * FROM jobs ORDER BY created_at, id").fetchall()
        return [JobRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[JobRecord]:
        rows = connection.execute(
            "SELECT * FROM jobs WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [JobRecord.from_row(row) for row in rows]

    def _list_by_agent_sync(
        self,
        connection: sqlite3.Connection,
        agent_id: str,
    ) -> list[JobRecord]:
        rows = connection.execute(
            "SELECT * FROM jobs WHERE assigned_agent_id = ? ORDER BY created_at, id",
            (agent_id,),
        ).fetchall()
        return [JobRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, job: JobRecord) -> JobRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE jobs SET
                    session_id = :session_id,
                    channel_key = :channel_key,
                    assigned_agent_id = :assigned_agent_id,
                    runtime_id = :runtime_id,
                    source_message_id = :source_message_id,
                    parent_job_id = :parent_job_id,
                    title = :title,
                    instructions = :instructions,
                    status = :status,
                    hop_count = :hop_count,
                    priority = :priority,
                    codex_runtime_id = :codex_runtime_id,
                    codex_thread_id = :codex_thread_id,
                    active_turn_id = :active_turn_id,
                    last_known_turn_status = :last_known_turn_status,
                    result_summary = :result_summary,
                    error_code = :error_code,
                    error_message = :error_message,
                    started_at = :started_at,
                    completed_at = :completed_at,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(job),
            )
        if result.rowcount == 0:
            raise LookupError(f"Job not found: {job.id}")
        return job

    def _delete_sync(self, connection: sqlite3.Connection, job_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return result.rowcount > 0


class JobEventRepository(SQLiteRepositoryBase):
    """CRUD access for job events."""

    async def create(self, event: JobEventRecord) -> JobEventRecord:
        return await self._run(lambda connection: self._create_sync(connection, event))

    async def get(self, event_id: str) -> JobEventRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, event_id))

    async def list(self) -> list[JobEventRecord]:
        return await self._run(self._list_sync)

    async def list_by_job(self, job_id: str) -> list[JobEventRecord]:
        return await self._run(lambda connection: self._list_by_job_sync(connection, job_id))

    async def list_by_session(self, session_id: str) -> list[JobEventRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def update(self, event: JobEventRecord) -> JobEventRecord:
        return await self._run(lambda connection: self._update_sync(connection, event))

    async def delete(self, event_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, event_id))

    def _create_sync(self, connection: sqlite3.Connection, event: JobEventRecord) -> JobEventRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO job_events (
                    id, job_id, session_id, event_type, event_payload_json, created_at
                ) VALUES (
                    :id, :job_id, :session_id, :event_type, :event_payload_json, :created_at
                )
                """,
                asdict(event),
            )
        return event

    def _get_sync(self, connection: sqlite3.Connection, event_id: str) -> JobEventRecord | None:
        row = connection.execute("SELECT * FROM job_events WHERE id = ?", (event_id,)).fetchone()
        return JobEventRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[JobEventRecord]:
        rows = connection.execute("SELECT * FROM job_events ORDER BY created_at, id").fetchall()
        return [JobEventRecord.from_row(row) for row in rows]

    def _list_by_job_sync(
        self,
        connection: sqlite3.Connection,
        job_id: str,
    ) -> list[JobEventRecord]:
        rows = connection.execute(
            "SELECT * FROM job_events WHERE job_id = ? ORDER BY created_at, id",
            (job_id,),
        ).fetchall()
        return [JobEventRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[JobEventRecord]:
        rows = connection.execute(
            "SELECT * FROM job_events WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [JobEventRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, event: JobEventRecord) -> JobEventRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE job_events SET
                    job_id = :job_id,
                    session_id = :session_id,
                    event_type = :event_type,
                    event_payload_json = :event_payload_json,
                    created_at = :created_at
                WHERE id = :id
                """,
                asdict(event),
            )
        if result.rowcount == 0:
            raise LookupError(f"Job event not found: {event.id}")
        return event

    def _delete_sync(self, connection: sqlite3.Connection, event_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM job_events WHERE id = ?", (event_id,))
        return result.rowcount > 0
