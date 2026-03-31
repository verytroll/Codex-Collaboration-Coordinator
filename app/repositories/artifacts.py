"""Artifact repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """Artifact row."""

    id: str
    job_id: str
    session_id: str
    source_message_id: str | None
    artifact_type: str
    title: str
    content_text: str | None
    file_path: str | None
    file_name: str | None
    mime_type: str | None
    size_bytes: int | None
    checksum_sha256: str | None
    metadata_json: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ArtifactRecord":
        return cls(
            id=row["id"],
            job_id=row["job_id"],
            session_id=row["session_id"],
            source_message_id=row["source_message_id"],
            artifact_type=row["artifact_type"],
            title=row["title"],
            content_text=row["content_text"],
            file_path=row["file_path"],
            file_name=row["file_name"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            checksum_sha256=row["checksum_sha256"],
            metadata_json=row["metadata_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class ArtifactRepository(SQLiteRepositoryBase):
    """CRUD access for artifacts."""

    async def create(self, artifact: ArtifactRecord) -> ArtifactRecord:
        return await self._run(lambda connection: self._create_sync(connection, artifact))

    async def get(self, artifact_id: str) -> ArtifactRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, artifact_id))

    async def list(self) -> list[ArtifactRecord]:
        return await self._run(self._list_sync)

    async def list_by_job(self, job_id: str) -> list[ArtifactRecord]:
        return await self._run(lambda connection: self._list_by_job_sync(connection, job_id))

    async def list_by_session(self, session_id: str) -> list[ArtifactRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def update(self, artifact: ArtifactRecord) -> ArtifactRecord:
        return await self._run(lambda connection: self._update_sync(connection, artifact))

    async def delete(self, artifact_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, artifact_id))

    def _create_sync(
        self, connection: sqlite3.Connection, artifact: ArtifactRecord
    ) -> ArtifactRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO artifacts (
                    id, job_id, session_id, source_message_id, artifact_type,
                    title, content_text, file_path, file_name, mime_type, size_bytes,
                    checksum_sha256, metadata_json, created_at, updated_at
                ) VALUES (
                    :id, :job_id, :session_id, :source_message_id, :artifact_type,
                    :title, :content_text, :file_path, :file_name, :mime_type, :size_bytes,
                    :checksum_sha256, :metadata_json, :created_at, :updated_at
                )
                """,
                asdict(artifact),
            )
        return artifact

    def _get_sync(self, connection: sqlite3.Connection, artifact_id: str) -> ArtifactRecord | None:
        row = connection.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        return ArtifactRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[ArtifactRecord]:
        rows = connection.execute("SELECT * FROM artifacts ORDER BY created_at, id").fetchall()
        return [ArtifactRecord.from_row(row) for row in rows]

    def _list_by_job_sync(
        self,
        connection: sqlite3.Connection,
        job_id: str,
    ) -> list[ArtifactRecord]:
        rows = connection.execute(
            "SELECT * FROM artifacts WHERE job_id = ? ORDER BY created_at, id",
            (job_id,),
        ).fetchall()
        return [ArtifactRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[ArtifactRecord]:
        rows = connection.execute(
            "SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [ArtifactRecord.from_row(row) for row in rows]

    def _update_sync(
        self, connection: sqlite3.Connection, artifact: ArtifactRecord
    ) -> ArtifactRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE artifacts SET
                    job_id = :job_id,
                    session_id = :session_id,
                    source_message_id = :source_message_id,
                    artifact_type = :artifact_type,
                    title = :title,
                    content_text = :content_text,
                    file_path = :file_path,
                    file_name = :file_name,
                    mime_type = :mime_type,
                    size_bytes = :size_bytes,
                    checksum_sha256 = :checksum_sha256,
                    metadata_json = :metadata_json,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(artifact),
            )
        if result.rowcount == 0:
            raise LookupError(f"Artifact not found: {artifact.id}")
        return artifact

    def _delete_sync(self, connection: sqlite3.Connection, artifact_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM artifacts WHERE id = ?", (artifact_id,))
        return result.rowcount > 0
