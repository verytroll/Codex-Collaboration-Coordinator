"""Approval request repository."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import sqlite3

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class ApprovalRequestRecord:
    """Approval request row."""

    id: str
    job_id: str
    agent_id: str
    approval_type: str
    status: str
    request_payload_json: str
    decision_payload_json: str | None
    requested_at: str
    resolved_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ApprovalRequestRecord":
        return cls(
            id=row["id"],
            job_id=row["job_id"],
            agent_id=row["agent_id"],
            approval_type=row["approval_type"],
            status=row["status"],
            request_payload_json=row["request_payload_json"],
            decision_payload_json=row["decision_payload_json"],
            requested_at=row["requested_at"],
            resolved_at=row["resolved_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class ApprovalRepository(SQLiteRepositoryBase):
    """CRUD access for approval requests."""

    async def create(self, approval: ApprovalRequestRecord) -> ApprovalRequestRecord:
        return await self._run(lambda connection: self._create_sync(connection, approval))

    async def get(self, approval_id: str) -> ApprovalRequestRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, approval_id))

    async def list(self) -> list[ApprovalRequestRecord]:
        return await self._run(self._list_sync)

    async def list_by_job(self, job_id: str) -> list[ApprovalRequestRecord]:
        return await self._run(lambda connection: self._list_by_job_sync(connection, job_id))

    async def list_by_agent(self, agent_id: str) -> list[ApprovalRequestRecord]:
        return await self._run(lambda connection: self._list_by_agent_sync(connection, agent_id))

    async def update(self, approval: ApprovalRequestRecord) -> ApprovalRequestRecord:
        return await self._run(lambda connection: self._update_sync(connection, approval))

    async def delete(self, approval_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, approval_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        approval: ApprovalRequestRecord,
    ) -> ApprovalRequestRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO approval_requests (
                    id, job_id, agent_id, approval_type, status,
                    request_payload_json, decision_payload_json, requested_at,
                    resolved_at, created_at, updated_at
                ) VALUES (
                    :id, :job_id, :agent_id, :approval_type, :status,
                    :request_payload_json, :decision_payload_json, :requested_at,
                    :resolved_at, :created_at, :updated_at
                )
                """,
                asdict(approval),
            )
        return approval

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        approval_id: str,
    ) -> ApprovalRequestRecord | None:
        row = connection.execute(
            "SELECT * FROM approval_requests WHERE id = ?",
            (approval_id,),
        ).fetchone()
        return ApprovalRequestRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[ApprovalRequestRecord]:
        rows = connection.execute("SELECT * FROM approval_requests ORDER BY created_at, id").fetchall()
        return [ApprovalRequestRecord.from_row(row) for row in rows]

    def _list_by_job_sync(
        self,
        connection: sqlite3.Connection,
        job_id: str,
    ) -> list[ApprovalRequestRecord]:
        rows = connection.execute(
            "SELECT * FROM approval_requests WHERE job_id = ? ORDER BY created_at, id",
            (job_id,),
        ).fetchall()
        return [ApprovalRequestRecord.from_row(row) for row in rows]

    def _list_by_agent_sync(
        self,
        connection: sqlite3.Connection,
        agent_id: str,
    ) -> list[ApprovalRequestRecord]:
        rows = connection.execute(
            "SELECT * FROM approval_requests WHERE agent_id = ? ORDER BY created_at, id",
            (agent_id,),
        ).fetchall()
        return [ApprovalRequestRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        approval: ApprovalRequestRecord,
    ) -> ApprovalRequestRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE approval_requests SET
                    job_id = :job_id,
                    agent_id = :agent_id,
                    approval_type = :approval_type,
                    status = :status,
                    request_payload_json = :request_payload_json,
                    decision_payload_json = :decision_payload_json,
                    requested_at = :requested_at,
                    resolved_at = :resolved_at,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(approval),
            )
        if result.rowcount == 0:
            raise LookupError(f"Approval request not found: {approval.id}")
        return approval

    def _delete_sync(self, connection: sqlite3.Connection, approval_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM approval_requests WHERE id = ?", (approval_id,))
        return result.rowcount > 0
