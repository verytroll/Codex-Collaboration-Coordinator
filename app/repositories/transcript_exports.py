"""Transcript export repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class TranscriptExportRecord:
    """Transcript export row."""

    id: str
    session_id: str
    export_kind: str
    export_format: str
    title: str
    file_name: str
    mime_type: str
    content_text: str
    size_bytes: int
    checksum_sha256: str
    metadata_json: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TranscriptExportRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            export_kind=row["export_kind"],
            export_format=row["export_format"],
            title=row["title"],
            file_name=row["file_name"],
            mime_type=row["mime_type"],
            content_text=row["content_text"],
            size_bytes=row["size_bytes"],
            checksum_sha256=row["checksum_sha256"],
            metadata_json=row["metadata_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class TranscriptExportRepository(SQLiteRepositoryBase):
    """CRUD access for transcript exports."""

    async def create(self, export: TranscriptExportRecord) -> TranscriptExportRecord:
        return await self._run(lambda connection: self._create_sync(connection, export))

    async def get(self, export_id: str) -> TranscriptExportRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, export_id))

    async def list(self) -> list[TranscriptExportRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[TranscriptExportRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def update(self, export: TranscriptExportRecord) -> TranscriptExportRecord:
        return await self._run(lambda connection: self._update_sync(connection, export))

    async def delete(self, export_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, export_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        export: TranscriptExportRecord,
    ) -> TranscriptExportRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO transcript_exports (
                    id, session_id, export_kind, export_format, title, file_name, mime_type,
                    content_text, size_bytes, checksum_sha256, metadata_json, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :export_kind, :export_format, :title, :file_name,
                    :mime_type, :content_text, :size_bytes, :checksum_sha256,
                    :metadata_json, :created_at, :updated_at
                )
                """,
                asdict(export),
            )
        return export

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        export_id: str,
    ) -> TranscriptExportRecord | None:
        row = connection.execute(
            "SELECT * FROM transcript_exports WHERE id = ?",
            (export_id,),
        ).fetchone()
        return TranscriptExportRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[TranscriptExportRecord]:
        rows = connection.execute(
            "SELECT * FROM transcript_exports ORDER BY created_at, id"
        ).fetchall()
        return [TranscriptExportRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[TranscriptExportRecord]:
        rows = connection.execute(
            """
            SELECT * FROM transcript_exports
            WHERE session_id = ?
            ORDER BY created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [TranscriptExportRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        export: TranscriptExportRecord,
    ) -> TranscriptExportRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE transcript_exports SET
                    session_id = :session_id,
                    export_kind = :export_kind,
                    export_format = :export_format,
                    title = :title,
                    file_name = :file_name,
                    mime_type = :mime_type,
                    content_text = :content_text,
                    size_bytes = :size_bytes,
                    checksum_sha256 = :checksum_sha256,
                    metadata_json = :metadata_json,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(export),
            )
        if result.rowcount == 0:
            raise LookupError(f"Transcript export not found: {export.id}")
        return export

    def _delete_sync(self, connection: sqlite3.Connection, export_id: str) -> bool:
        with connection:
            result = connection.execute(
                "DELETE FROM transcript_exports WHERE id = ?",
                (export_id,),
            )
        return result.rowcount > 0
