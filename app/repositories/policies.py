"""Policy repository for advanced automation rules."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from typing import Any

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class PolicyRecord:
    """Advanced policy row."""

    id: str
    session_id: str | None
    template_key: str | None
    phase_key: str | None
    policy_type: str
    name: str
    description: str | None
    is_active: int
    automation_paused: int
    pause_reason: str | None
    priority: int
    conditions_json: str | None
    actions_json: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PolicyRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            template_key=row["template_key"],
            phase_key=row["phase_key"],
            policy_type=row["policy_type"],
            name=row["name"],
            description=row["description"],
            is_active=row["is_active"],
            automation_paused=row["automation_paused"],
            pause_reason=row["pause_reason"],
            priority=row["priority"],
            conditions_json=row["conditions_json"],
            actions_json=row["actions_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True, slots=True)
class PolicyDecisionRecord:
    """Policy decision audit row."""

    id: str
    policy_id: str | None
    session_id: str | None
    subject_type: str
    subject_id: str
    gate_type: str
    decision: str
    matched: int
    reason: str
    context_json: str
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PolicyDecisionRecord":
        return cls(
            id=row["id"],
            policy_id=row["policy_id"],
            session_id=row["session_id"],
            subject_type=row["subject_type"],
            subject_id=row["subject_id"],
            gate_type=row["gate_type"],
            decision=row["decision"],
            matched=row["matched"],
            reason=row["reason"],
            context_json=row["context_json"],
            created_at=row["created_at"],
        )


class PolicyRepository(SQLiteRepositoryBase):
    """CRUD and audit access for advanced policies."""

    async def create(self, policy: PolicyRecord) -> PolicyRecord:
        return await self._run(lambda connection: self._create_sync(connection, policy))

    async def get(self, policy_id: str) -> PolicyRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, policy_id))

    async def list(
        self,
        *,
        session_id: str | None = None,
        template_key: str | None = None,
        phase_key: str | None = None,
        active_only: bool = False,
    ) -> list[PolicyRecord]:
        return await self._run(
            lambda connection: self._list_sync(
                connection,
                session_id=session_id,
                template_key=template_key,
                phase_key=phase_key,
                active_only=active_only,
            )
        )

    async def update(self, policy: PolicyRecord) -> PolicyRecord:
        return await self._run(lambda connection: self._update_sync(connection, policy))

    async def create_decision(
        self,
        decision: PolicyDecisionRecord,
    ) -> PolicyDecisionRecord:
        return await self._run(lambda connection: self._create_decision_sync(connection, decision))

    async def list_decisions(
        self,
        *,
        policy_id: str | None = None,
        session_id: str | None = None,
    ) -> list[PolicyDecisionRecord]:
        return await self._run(
            lambda connection: self._list_decisions_sync(
                connection,
                policy_id=policy_id,
                session_id=session_id,
            )
        )

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        policy: PolicyRecord,
    ) -> PolicyRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO policies (
                    id, session_id, template_key, phase_key, policy_type, name,
                    description, is_active, automation_paused, pause_reason,
                    priority, conditions_json, actions_json, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :template_key, :phase_key, :policy_type, :name,
                    :description, :is_active, :automation_paused, :pause_reason,
                    :priority, :conditions_json, :actions_json, :created_at, :updated_at
                )
                """,
                asdict(policy),
            )
        return policy

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        policy_id: str,
    ) -> PolicyRecord | None:
        row = connection.execute("SELECT * FROM policies WHERE id = ?", (policy_id,)).fetchone()
        return PolicyRecord.from_row(row) if row else None

    def _list_sync(
        self,
        connection: sqlite3.Connection,
        *,
        session_id: str | None,
        template_key: str | None,
        phase_key: str | None,
        active_only: bool,
    ) -> list[PolicyRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if active_only:
            clauses.append("is_active = 1")
            clauses.append("automation_paused = 0")

        scope_clauses: list[str] = []
        if session_id is not None:
            scope_clauses.append("session_id = ?")
            params.append(session_id)
        if template_key is not None:
            scope_clauses.append("template_key = ?")
            params.append(template_key)
        if phase_key is not None:
            scope_clauses.append("phase_key = ?")
            params.append(phase_key)
        if scope_clauses:
            clauses.append(f"({' OR '.join(scope_clauses)})")

        sql = "SELECT * FROM policies"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY priority, created_at, id"
        rows = connection.execute(sql, params).fetchall()
        return [PolicyRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        policy: PolicyRecord,
    ) -> PolicyRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE policies SET
                    session_id = :session_id,
                    template_key = :template_key,
                    phase_key = :phase_key,
                    policy_type = :policy_type,
                    name = :name,
                    description = :description,
                    is_active = :is_active,
                    automation_paused = :automation_paused,
                    pause_reason = :pause_reason,
                    priority = :priority,
                    conditions_json = :conditions_json,
                    actions_json = :actions_json,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(policy),
            )
        if result.rowcount == 0:
            raise LookupError(f"Policy not found: {policy.id}")
        return policy

    def _create_decision_sync(
        self,
        connection: sqlite3.Connection,
        decision: PolicyDecisionRecord,
    ) -> PolicyDecisionRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO policy_decisions (
                    id, policy_id, session_id, subject_type, subject_id, gate_type,
                    decision, matched, reason, context_json, created_at
                ) VALUES (
                    :id, :policy_id, :session_id, :subject_type, :subject_id, :gate_type,
                    :decision, :matched, :reason, :context_json, :created_at
                )
                """,
                asdict(decision),
            )
        return decision

    def _list_decisions_sync(
        self,
        connection: sqlite3.Connection,
        *,
        policy_id: str | None,
        session_id: str | None,
    ) -> list[PolicyDecisionRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if policy_id is not None:
            clauses.append("policy_id = ?")
            params.append(policy_id)
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)

        sql = "SELECT * FROM policy_decisions"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at, id"
        rows = connection.execute(sql, params).fetchall()
        return [PolicyDecisionRecord.from_row(row) for row in rows]
