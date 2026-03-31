"""Rule repository for session-scoped collaboration policy."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class RuleRecord:
    """Rule row."""

    id: str
    session_id: str
    rule_type: str
    name: str
    description: str | None
    is_active: int
    priority: int
    conditions_json: str | None
    actions_json: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RuleRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            rule_type=row["rule_type"],
            name=row["name"],
            description=row["description"],
            is_active=row["is_active"],
            priority=row["priority"],
            conditions_json=row["conditions_json"],
            actions_json=row["actions_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class RuleRepository(SQLiteRepositoryBase):
    """CRUD access for collaboration rules."""

    async def create(self, rule: RuleRecord) -> RuleRecord:
        return await self._run(lambda connection: self._create_sync(connection, rule))

    async def get(self, rule_id: str) -> RuleRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, rule_id))

    async def list(self) -> list[RuleRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[RuleRecord]:
        return await self._run(lambda connection: self._list_by_session_sync(connection, session_id))

    async def list_active_by_session(self, session_id: str) -> list[RuleRecord]:
        return await self._run(
            lambda connection: self._list_active_by_session_sync(connection, session_id)
        )

    async def update(self, rule: RuleRecord) -> RuleRecord:
        return await self._run(lambda connection: self._update_sync(connection, rule))

    async def delete(self, rule_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, rule_id))

    def _create_sync(self, connection: sqlite3.Connection, rule: RuleRecord) -> RuleRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO rules (
                    id, session_id, rule_type, name, description, is_active,
                    priority, conditions_json, actions_json, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :rule_type, :name, :description, :is_active,
                    :priority, :conditions_json, :actions_json, :created_at, :updated_at
                )
                """,
                asdict(rule),
            )
        return rule

    def _get_sync(self, connection: sqlite3.Connection, rule_id: str) -> RuleRecord | None:
        row = connection.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
        return RuleRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[RuleRecord]:
        rows = connection.execute("SELECT * FROM rules ORDER BY session_id, priority, id").fetchall()
        return [RuleRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[RuleRecord]:
        rows = connection.execute(
            """
            SELECT * FROM rules
            WHERE session_id = ?
            ORDER BY priority, created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [RuleRecord.from_row(row) for row in rows]

    def _list_active_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[RuleRecord]:
        rows = connection.execute(
            """
            SELECT * FROM rules
            WHERE session_id = ? AND is_active = 1
            ORDER BY priority, created_at, id
            """,
            (session_id,),
        ).fetchall()
        return [RuleRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, rule: RuleRecord) -> RuleRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE rules SET
                    session_id = :session_id,
                    rule_type = :rule_type,
                    name = :name,
                    description = :description,
                    is_active = :is_active,
                    priority = :priority,
                    conditions_json = :conditions_json,
                    actions_json = :actions_json,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(rule),
            )
        if result.rowcount == 0:
            raise LookupError(f"Rule not found: {rule.id}")
        return rule

    def _delete_sync(self, connection: sqlite3.Connection, rule_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        return result.rowcount > 0
