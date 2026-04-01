"""Session template repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class SessionTemplateRecord:
    """Session template row."""

    id: str
    template_key: str
    title: str
    description: str | None
    default_goal: str | None
    participant_roles_json: str
    channels_json: str
    phase_order_json: str
    rule_presets_json: str
    orchestration_json: str | None
    is_default: int
    sort_order: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SessionTemplateRecord":
        return cls(
            id=row["id"],
            template_key=row["template_key"],
            title=row["title"],
            description=row["description"],
            default_goal=row["default_goal"],
            participant_roles_json=row["participant_roles_json"],
            channels_json=row["channels_json"],
            phase_order_json=row["phase_order_json"],
            rule_presets_json=row["rule_presets_json"],
            orchestration_json=row["orchestration_json"],
            is_default=row["is_default"],
            sort_order=row["sort_order"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class SessionTemplateRepository(SQLiteRepositoryBase):
    """CRUD access for session templates."""

    async def create(self, template: SessionTemplateRecord) -> SessionTemplateRecord:
        return await self._run(lambda connection: self._create_sync(connection, template))

    async def get(self, template_id: str) -> SessionTemplateRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, template_id))

    async def get_by_key(self, template_key: str) -> SessionTemplateRecord | None:
        return await self._run(lambda connection: self._get_by_key_sync(connection, template_key))

    async def list(self) -> list[SessionTemplateRecord]:
        return await self._run(self._list_sync)

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        template: SessionTemplateRecord,
    ) -> SessionTemplateRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO session_templates (
                    id, template_key, title, description, default_goal,
                    participant_roles_json, channels_json, phase_order_json,
                    rule_presets_json, orchestration_json, is_default, sort_order,
                    created_at, updated_at
                ) VALUES (
                    :id, :template_key, :title, :description, :default_goal,
                    :participant_roles_json, :channels_json, :phase_order_json,
                    :rule_presets_json, :orchestration_json, :is_default, :sort_order,
                    :created_at, :updated_at
                )
                """,
                asdict(template),
            )
        return template

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        template_id: str,
    ) -> SessionTemplateRecord | None:
        row = connection.execute(
            "SELECT * FROM session_templates WHERE id = ?",
            (template_id,),
        ).fetchone()
        return SessionTemplateRecord.from_row(row) if row else None

    def _get_by_key_sync(
        self,
        connection: sqlite3.Connection,
        template_key: str,
    ) -> SessionTemplateRecord | None:
        row = connection.execute(
            "SELECT * FROM session_templates WHERE template_key = ?",
            (template_key,),
        ).fetchone()
        return SessionTemplateRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[SessionTemplateRecord]:
        rows = connection.execute(
            """
            SELECT * FROM session_templates
            ORDER BY is_default DESC, sort_order, title, template_key
            """
        ).fetchall()
        return [SessionTemplateRecord.from_row(row) for row in rows]
