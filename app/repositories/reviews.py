"""Review mode repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """Session review row."""

    id: str
    session_id: str
    source_job_id: str
    reviewer_agent_id: str
    requested_by_agent_id: str | None
    review_scope: str
    review_status: str
    review_channel_key: str
    template_key: str
    request_message_id: str | None
    decision_message_id: str | None
    summary_artifact_id: str | None
    revision_job_id: str | None
    request_payload_json: str | None
    decision_payload_json: str | None
    requested_at: str
    decided_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ReviewRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            source_job_id=row["source_job_id"],
            reviewer_agent_id=row["reviewer_agent_id"],
            requested_by_agent_id=row["requested_by_agent_id"],
            review_scope=row["review_scope"],
            review_status=row["review_status"],
            review_channel_key=row["review_channel_key"],
            template_key=row["template_key"],
            request_message_id=row["request_message_id"],
            decision_message_id=row["decision_message_id"],
            summary_artifact_id=row["summary_artifact_id"],
            revision_job_id=row["revision_job_id"],
            request_payload_json=row["request_payload_json"],
            decision_payload_json=row["decision_payload_json"],
            requested_at=row["requested_at"],
            decided_at=row["decided_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class ReviewRepository(SQLiteRepositoryBase):
    """CRUD access for review records."""

    async def create(self, review: ReviewRecord) -> ReviewRecord:
        return await self._run(lambda connection: self._create_sync(connection, review))

    async def get(self, review_id: str) -> ReviewRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, review_id))

    async def list(self) -> list[ReviewRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[ReviewRecord]:
        return await self._run(lambda connection: self._list_by_session_sync(connection, session_id))

    async def list_by_job(self, job_id: str) -> list[ReviewRecord]:
        return await self._run(lambda connection: self._list_by_job_sync(connection, job_id))

    async def list_active_by_session(self, session_id: str) -> list[ReviewRecord]:
        return await self._run(
            lambda connection: self._list_active_by_session_sync(connection, session_id)
        )

    async def update(self, review: ReviewRecord) -> ReviewRecord:
        return await self._run(lambda connection: self._update_sync(connection, review))

    async def delete(self, review_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, review_id))

    def _create_sync(self, connection: sqlite3.Connection, review: ReviewRecord) -> ReviewRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO session_reviews (
                    id, session_id, source_job_id, reviewer_agent_id, requested_by_agent_id,
                    review_scope, review_status, review_channel_key, template_key,
                    request_message_id, decision_message_id, summary_artifact_id, revision_job_id,
                    request_payload_json, decision_payload_json, requested_at, decided_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :session_id, :source_job_id, :reviewer_agent_id,
                    :requested_by_agent_id, :review_scope, :review_status,
                    :review_channel_key, :template_key, :request_message_id,
                    :decision_message_id, :summary_artifact_id, :revision_job_id,
                    :request_payload_json, :decision_payload_json, :requested_at,
                    :decided_at, :created_at, :updated_at
                )
                """,
                asdict(review),
            )
        return review

    def _get_sync(self, connection: sqlite3.Connection, review_id: str) -> ReviewRecord | None:
        row = connection.execute(
            "SELECT * FROM session_reviews WHERE id = ?",
            (review_id,),
        ).fetchone()
        return ReviewRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[ReviewRecord]:
        rows = connection.execute(
            "SELECT * FROM session_reviews ORDER BY created_at, id"
        ).fetchall()
        return [ReviewRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[ReviewRecord]:
        rows = connection.execute(
            """
            SELECT * FROM session_reviews
            WHERE session_id = ?
            ORDER BY created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [ReviewRecord.from_row(row) for row in rows]

    def _list_by_job_sync(
        self,
        connection: sqlite3.Connection,
        job_id: str,
    ) -> list[ReviewRecord]:
        rows = connection.execute(
            """
            SELECT * FROM session_reviews
            WHERE source_job_id = ?
            ORDER BY created_at, id
            """,
            (job_id,),
        ).fetchall()
        return [ReviewRecord.from_row(row) for row in rows]

    def _list_active_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[ReviewRecord]:
        rows = connection.execute(
            """
            SELECT * FROM session_reviews
            WHERE session_id = ? AND review_status = 'requested'
            ORDER BY created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [ReviewRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, review: ReviewRecord) -> ReviewRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE session_reviews SET
                    session_id = :session_id,
                    source_job_id = :source_job_id,
                    reviewer_agent_id = :reviewer_agent_id,
                    requested_by_agent_id = :requested_by_agent_id,
                    review_scope = :review_scope,
                    review_status = :review_status,
                    review_channel_key = :review_channel_key,
                    template_key = :template_key,
                    request_message_id = :request_message_id,
                    decision_message_id = :decision_message_id,
                    summary_artifact_id = :summary_artifact_id,
                    revision_job_id = :revision_job_id,
                    request_payload_json = :request_payload_json,
                    decision_payload_json = :decision_payload_json,
                    requested_at = :requested_at,
                    decided_at = :decided_at,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(review),
            )
        if result.rowcount == 0:
            raise LookupError(f"Review not found: {review.id}")
        return review

    def _delete_sync(self, connection: sqlite3.Connection, review_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM session_reviews WHERE id = ?", (review_id,))
        return result.rowcount > 0
