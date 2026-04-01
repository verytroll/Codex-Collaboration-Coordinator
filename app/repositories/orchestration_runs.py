"""Orchestration run repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class OrchestrationRunRecord:
    """Orchestration run row."""

    id: str
    session_id: str
    status: str
    current_phase_id: str | None
    current_phase_key: str
    pending_phase_key: str | None
    failure_phase_key: str
    gate_type: str | None
    gate_status: str
    source_job_id: str | None
    handoff_job_id: str | None
    review_id: str | None
    approval_id: str | None
    transition_artifact_id: str | None
    decision_artifact_id: str | None
    revision_job_id: str | None
    requested_by_agent_id: str | None
    transition_reason: str | None
    started_at: str
    decided_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "OrchestrationRunRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            status=row["status"],
            current_phase_id=row["current_phase_id"],
            current_phase_key=row["current_phase_key"],
            pending_phase_key=row["pending_phase_key"],
            failure_phase_key=row["failure_phase_key"],
            gate_type=row["gate_type"],
            gate_status=row["gate_status"],
            source_job_id=row["source_job_id"],
            handoff_job_id=row["handoff_job_id"],
            review_id=row["review_id"],
            approval_id=row["approval_id"],
            transition_artifact_id=row["transition_artifact_id"],
            decision_artifact_id=row["decision_artifact_id"],
            revision_job_id=row["revision_job_id"],
            requested_by_agent_id=row["requested_by_agent_id"],
            transition_reason=row["transition_reason"],
            started_at=row["started_at"],
            decided_at=row["decided_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class OrchestrationRunRepository(SQLiteRepositoryBase):
    """CRUD access for orchestration runs."""

    async def create(self, run: OrchestrationRunRecord) -> OrchestrationRunRecord:
        return await self._run(lambda connection: self._create_sync(connection, run))

    async def get(self, run_id: str) -> OrchestrationRunRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, run_id))

    async def get_by_session(self, session_id: str) -> OrchestrationRunRecord | None:
        return await self._run(lambda connection: self._get_by_session_sync(connection, session_id))

    async def get_by_review_id(self, review_id: str) -> OrchestrationRunRecord | None:
        return await self._run(
            lambda connection: self._get_by_review_id_sync(connection, review_id)
        )

    async def get_by_approval_id(self, approval_id: str) -> OrchestrationRunRecord | None:
        return await self._run(
            lambda connection: self._get_by_approval_id_sync(connection, approval_id)
        )

    async def list(self) -> list[OrchestrationRunRecord]:
        return await self._run(self._list_sync)

    async def update(self, run: OrchestrationRunRecord) -> OrchestrationRunRecord:
        return await self._run(lambda connection: self._update_sync(connection, run))

    async def delete(self, run_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, run_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        run: OrchestrationRunRecord,
    ) -> OrchestrationRunRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO orchestration_runs (
                    id, session_id, status, current_phase_id, current_phase_key,
                    pending_phase_key, failure_phase_key, gate_type, gate_status,
                    source_job_id, handoff_job_id, review_id, approval_id,
                    transition_artifact_id, decision_artifact_id, revision_job_id,
                    requested_by_agent_id, transition_reason, started_at, decided_at,
                    completed_at, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :status, :current_phase_id, :current_phase_key,
                    :pending_phase_key, :failure_phase_key, :gate_type, :gate_status,
                    :source_job_id, :handoff_job_id, :review_id, :approval_id,
                    :transition_artifact_id, :decision_artifact_id, :revision_job_id,
                    :requested_by_agent_id, :transition_reason, :started_at, :decided_at,
                    :completed_at, :created_at, :updated_at
                )
                """,
                asdict(run),
            )
        return run

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        run_id: str,
    ) -> OrchestrationRunRecord | None:
        row = connection.execute(
            "SELECT * FROM orchestration_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return OrchestrationRunRecord.from_row(row) if row else None

    def _get_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> OrchestrationRunRecord | None:
        row = connection.execute(
            "SELECT * FROM orchestration_runs WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return OrchestrationRunRecord.from_row(row) if row else None

    def _get_by_review_id_sync(
        self,
        connection: sqlite3.Connection,
        review_id: str,
    ) -> OrchestrationRunRecord | None:
        row = connection.execute(
            "SELECT * FROM orchestration_runs WHERE review_id = ?",
            (review_id,),
        ).fetchone()
        return OrchestrationRunRecord.from_row(row) if row else None

    def _get_by_approval_id_sync(
        self,
        connection: sqlite3.Connection,
        approval_id: str,
    ) -> OrchestrationRunRecord | None:
        row = connection.execute(
            "SELECT * FROM orchestration_runs WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
        return OrchestrationRunRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[OrchestrationRunRecord]:
        rows = connection.execute(
            "SELECT * FROM orchestration_runs ORDER BY created_at, id"
        ).fetchall()
        return [OrchestrationRunRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        run: OrchestrationRunRecord,
    ) -> OrchestrationRunRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE orchestration_runs SET
                    session_id = :session_id,
                    status = :status,
                    current_phase_id = :current_phase_id,
                    current_phase_key = :current_phase_key,
                    pending_phase_key = :pending_phase_key,
                    failure_phase_key = :failure_phase_key,
                    gate_type = :gate_type,
                    gate_status = :gate_status,
                    source_job_id = :source_job_id,
                    handoff_job_id = :handoff_job_id,
                    review_id = :review_id,
                    approval_id = :approval_id,
                    transition_artifact_id = :transition_artifact_id,
                    decision_artifact_id = :decision_artifact_id,
                    revision_job_id = :revision_job_id,
                    requested_by_agent_id = :requested_by_agent_id,
                    transition_reason = :transition_reason,
                    started_at = :started_at,
                    decided_at = :decided_at,
                    completed_at = :completed_at,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(run),
            )
        if result.rowcount == 0:
            raise LookupError(f"Orchestration run not found: {run.id}")
        return run

    def _delete_sync(self, connection: sqlite3.Connection, run_id: str) -> bool:
        with connection:
            result = connection.execute(
                "DELETE FROM orchestration_runs WHERE id = ?",
                (run_id,),
            )
        return result.rowcount > 0
