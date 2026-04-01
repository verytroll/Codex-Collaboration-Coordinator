"""Experimental A2A task mapping repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class A2ATaskRecord:
    """A2A task mapping row."""

    id: str
    session_id: str
    job_id: str
    phase_id: str | None
    task_id: str
    context_id: str
    task_status: str
    relay_template_key: str | None
    primary_artifact_id: str | None
    task_payload_json: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "A2ATaskRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            job_id=row["job_id"],
            phase_id=row["phase_id"],
            task_id=row["task_id"],
            context_id=row["context_id"],
            task_status=row["task_status"],
            relay_template_key=row["relay_template_key"],
            primary_artifact_id=row["primary_artifact_id"],
            task_payload_json=row["task_payload_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class A2ATaskRepository(SQLiteRepositoryBase):
    """CRUD access for A2A task mappings."""

    async def create(self, task: A2ATaskRecord) -> A2ATaskRecord:
        return await self._run(lambda connection: self._create_sync(connection, task))

    async def get(self, task_id: str) -> A2ATaskRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, task_id))

    async def get_by_job(self, job_id: str) -> A2ATaskRecord | None:
        return await self._run(lambda connection: self._get_by_job_sync(connection, job_id))

    async def list(self) -> list[A2ATaskRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[A2ATaskRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def update(self, task: A2ATaskRecord) -> A2ATaskRecord:
        return await self._run(lambda connection: self._update_sync(connection, task))

    async def delete(self, task_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, task_id))

    def _create_sync(self, connection: sqlite3.Connection, task: A2ATaskRecord) -> A2ATaskRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO a2a_tasks (
                    id, session_id, job_id, phase_id, task_id, context_id, task_status,
                    relay_template_key, primary_artifact_id, task_payload_json,
                    created_at, updated_at
                ) VALUES (
                    :id, :session_id, :job_id, :phase_id, :task_id, :context_id, :task_status,
                    :relay_template_key, :primary_artifact_id, :task_payload_json,
                    :created_at, :updated_at
                )
                """,
                asdict(task),
            )
        return task

    def _get_sync(self, connection: sqlite3.Connection, task_id: str) -> A2ATaskRecord | None:
        row = connection.execute("SELECT * FROM a2a_tasks WHERE task_id = ?", (task_id,)).fetchone()
        return A2ATaskRecord.from_row(row) if row else None

    def _get_by_job_sync(self, connection: sqlite3.Connection, job_id: str) -> A2ATaskRecord | None:
        row = connection.execute("SELECT * FROM a2a_tasks WHERE job_id = ?", (job_id,)).fetchone()
        return A2ATaskRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[A2ATaskRecord]:
        rows = connection.execute("SELECT * FROM a2a_tasks ORDER BY created_at, id").fetchall()
        return [A2ATaskRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[A2ATaskRecord]:
        rows = connection.execute(
            "SELECT * FROM a2a_tasks WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [A2ATaskRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, task: A2ATaskRecord) -> A2ATaskRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE a2a_tasks SET
                    session_id = :session_id,
                    job_id = :job_id,
                    phase_id = :phase_id,
                    task_id = :task_id,
                    context_id = :context_id,
                    task_status = :task_status,
                    relay_template_key = :relay_template_key,
                    primary_artifact_id = :primary_artifact_id,
                    task_payload_json = :task_payload_json,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(task),
            )
        if result.rowcount == 0:
            raise LookupError(f"A2A task not found: {task.id}")
        return task

    def _delete_sync(self, connection: sqlite3.Connection, task_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM a2a_tasks WHERE task_id = ?", (task_id,))
        return result.rowcount > 0
