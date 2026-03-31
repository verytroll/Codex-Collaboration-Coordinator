"""Job input repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class JobInputRecord:
    """Normalized input row for a job action."""

    id: str
    job_id: str
    session_id: str
    input_type: str
    input_payload_json: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "JobInputRecord":
        return cls(
            id=row["id"],
            job_id=row["job_id"],
            session_id=row["session_id"],
            input_type=row["input_type"],
            input_payload_json=row["input_payload_json"],
            created_at=row["created_at"],
        )


class JobInputRepository(SQLiteRepositoryBase):
    """CRUD access for normalized job inputs."""

    async def create(self, job_input: JobInputRecord) -> JobInputRecord:
        return await self._run(lambda connection: self._create_sync(connection, job_input))

    async def get(self, job_input_id: str) -> JobInputRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, job_input_id))

    async def list(self) -> list[JobInputRecord]:
        return await self._run(self._list_sync)

    async def list_by_job(self, job_id: str) -> list[JobInputRecord]:
        return await self._run(lambda connection: self._list_by_job_sync(connection, job_id))

    async def list_by_session(self, session_id: str) -> list[JobInputRecord]:
        return await self._run(lambda connection: self._list_by_session_sync(connection, session_id))

    async def update(self, job_input: JobInputRecord) -> JobInputRecord:
        return await self._run(lambda connection: self._update_sync(connection, job_input))

    async def delete(self, job_input_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, job_input_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        job_input: JobInputRecord,
    ) -> JobInputRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO job_inputs (
                    id, job_id, session_id, input_type, input_payload_json, created_at
                ) VALUES (
                    :id, :job_id, :session_id, :input_type, :input_payload_json, :created_at
                )
                """,
                asdict(job_input),
            )
        return job_input

    def _get_sync(self, connection: sqlite3.Connection, job_input_id: str) -> JobInputRecord | None:
        row = connection.execute(
            "SELECT * FROM job_inputs WHERE id = ?",
            (job_input_id,),
        ).fetchone()
        return JobInputRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[JobInputRecord]:
        rows = connection.execute("SELECT * FROM job_inputs ORDER BY created_at, id").fetchall()
        return [JobInputRecord.from_row(row) for row in rows]

    def _list_by_job_sync(
        self,
        connection: sqlite3.Connection,
        job_id: str,
    ) -> list[JobInputRecord]:
        rows = connection.execute(
            "SELECT * FROM job_inputs WHERE job_id = ? ORDER BY created_at, id",
            (job_id,),
        ).fetchall()
        return [JobInputRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[JobInputRecord]:
        rows = connection.execute(
            "SELECT * FROM job_inputs WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [JobInputRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        job_input: JobInputRecord,
    ) -> JobInputRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE job_inputs SET
                    job_id = :job_id,
                    session_id = :session_id,
                    input_type = :input_type,
                    input_payload_json = :input_payload_json,
                    created_at = :created_at
                WHERE id = :id
                """,
                asdict(job_input),
            )
        if result.rowcount == 0:
            raise LookupError(f"Job input not found: {job_input.id}")
        return job_input

    def _delete_sync(self, connection: sqlite3.Connection, job_input_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM job_inputs WHERE id = ?", (job_input_id,))
        return result.rowcount > 0
