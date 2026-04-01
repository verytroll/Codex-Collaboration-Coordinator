"""Runtime pool repository."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class RuntimePoolRecord:
    """Runtime pool row."""

    id: str
    pool_key: str
    title: str
    description: str | None
    runtime_kind: str
    preferred_transport_kind: str | None
    required_capabilities_json: str | None
    fallback_pool_key: str | None
    max_active_contexts: int
    default_isolation_mode: str
    pool_status: str
    metadata_json: str | None
    is_default: int
    sort_order: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RuntimePoolRecord":
        return cls(
            id=row["id"],
            pool_key=row["pool_key"],
            title=row["title"],
            description=row["description"],
            runtime_kind=row["runtime_kind"],
            preferred_transport_kind=row["preferred_transport_kind"],
            required_capabilities_json=row["required_capabilities_json"],
            fallback_pool_key=row["fallback_pool_key"],
            max_active_contexts=row["max_active_contexts"],
            default_isolation_mode=row["default_isolation_mode"],
            pool_status=row["pool_status"],
            metadata_json=row["metadata_json"],
            is_default=row["is_default"],
            sort_order=row["sort_order"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class RuntimePoolRepository(SQLiteRepositoryBase):
    """CRUD access for runtime pools."""

    async def create(self, pool: RuntimePoolRecord) -> RuntimePoolRecord:
        return await self._run(lambda connection: self._create_sync(connection, pool))

    async def get(self, pool_id: str) -> RuntimePoolRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, pool_id))

    async def get_by_key(self, pool_key: str) -> RuntimePoolRecord | None:
        return await self._run(lambda connection: self._get_by_key_sync(connection, pool_key))

    async def list(self) -> list[RuntimePoolRecord]:
        return await self._run(self._list_sync)

    async def update(self, pool: RuntimePoolRecord) -> RuntimePoolRecord:
        return await self._run(lambda connection: self._update_sync(connection, pool))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        pool: RuntimePoolRecord,
    ) -> RuntimePoolRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO runtime_pools (
                    id, pool_key, title, description, runtime_kind, preferred_transport_kind,
                    required_capabilities_json, fallback_pool_key, max_active_contexts,
                    default_isolation_mode, pool_status, metadata_json, is_default,
                    sort_order, created_at, updated_at
                ) VALUES (
                    :id, :pool_key, :title, :description, :runtime_kind, :preferred_transport_kind,
                    :required_capabilities_json, :fallback_pool_key, :max_active_contexts,
                    :default_isolation_mode, :pool_status, :metadata_json, :is_default,
                    :sort_order, :created_at, :updated_at
                )
                """,
                asdict(pool),
            )
        return pool

    def _get_sync(self, connection: sqlite3.Connection, pool_id: str) -> RuntimePoolRecord | None:
        row = connection.execute("SELECT * FROM runtime_pools WHERE id = ?", (pool_id,)).fetchone()
        return RuntimePoolRecord.from_row(row) if row else None

    def _get_by_key_sync(
        self,
        connection: sqlite3.Connection,
        pool_key: str,
    ) -> RuntimePoolRecord | None:
        row = connection.execute(
            "SELECT * FROM runtime_pools WHERE pool_key = ?",
            (pool_key,),
        ).fetchone()
        return RuntimePoolRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[RuntimePoolRecord]:
        rows = connection.execute(
            """
            SELECT * FROM runtime_pools
            ORDER BY is_default DESC, sort_order, title, pool_key
            """
        ).fetchall()
        return [RuntimePoolRecord.from_row(row) for row in rows]

    def _update_sync(
        self, connection: sqlite3.Connection, pool: RuntimePoolRecord
    ) -> RuntimePoolRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE runtime_pools SET
                    pool_key = :pool_key,
                    title = :title,
                    description = :description,
                    runtime_kind = :runtime_kind,
                    preferred_transport_kind = :preferred_transport_kind,
                    required_capabilities_json = :required_capabilities_json,
                    fallback_pool_key = :fallback_pool_key,
                    max_active_contexts = :max_active_contexts,
                    default_isolation_mode = :default_isolation_mode,
                    pool_status = :pool_status,
                    metadata_json = :metadata_json,
                    is_default = :is_default,
                    sort_order = :sort_order,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(pool),
            )
        if result.rowcount == 0:
            raise LookupError(f"Runtime pool not found: {pool.id}")
        return pool


@dataclass(frozen=True, slots=True)
class WorkContextRecord:
    """Work context row."""

    id: str
    session_id: str
    job_id: str
    agent_id: str
    runtime_pool_id: str
    runtime_id: str | None
    context_key: str
    workspace_path: str | None
    isolation_mode: str
    context_status: str
    ownership_state: str
    selection_reason: str | None
    failure_reason: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "WorkContextRecord":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            job_id=row["job_id"],
            agent_id=row["agent_id"],
            runtime_pool_id=row["runtime_pool_id"],
            runtime_id=row["runtime_id"],
            context_key=row["context_key"],
            workspace_path=row["workspace_path"],
            isolation_mode=row["isolation_mode"],
            context_status=row["context_status"],
            ownership_state=row["ownership_state"],
            selection_reason=row["selection_reason"],
            failure_reason=row["failure_reason"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class WorkContextRepository(SQLiteRepositoryBase):
    """CRUD access for work contexts."""

    async def create(self, context: WorkContextRecord) -> WorkContextRecord:
        return await self._run(lambda connection: self._create_sync(connection, context))

    async def get(self, context_id: str) -> WorkContextRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, context_id))

    async def get_by_job(self, job_id: str) -> WorkContextRecord | None:
        return await self._run(lambda connection: self._get_by_job_sync(connection, job_id))

    async def list(self) -> list[WorkContextRecord]:
        return await self._run(self._list_sync)

    async def list_by_session(self, session_id: str) -> list[WorkContextRecord]:
        return await self._run(
            lambda connection: self._list_by_session_sync(connection, session_id)
        )

    async def list_by_pool(self, runtime_pool_id: str) -> list[WorkContextRecord]:
        return await self._run(
            lambda connection: self._list_by_pool_sync(connection, runtime_pool_id)
        )

    async def list_by_agent(self, agent_id: str) -> list[WorkContextRecord]:
        return await self._run(lambda connection: self._list_by_agent_sync(connection, agent_id))

    async def update(self, context: WorkContextRecord) -> WorkContextRecord:
        return await self._run(lambda connection: self._update_sync(connection, context))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        context: WorkContextRecord,
    ) -> WorkContextRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO work_contexts (
                    id, session_id, job_id, agent_id, runtime_pool_id, runtime_id,
                    context_key, workspace_path, isolation_mode, context_status,
                    ownership_state, selection_reason, failure_reason, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :job_id, :agent_id, :runtime_pool_id, :runtime_id,
                    :context_key, :workspace_path, :isolation_mode, :context_status,
                    :ownership_state, :selection_reason, :failure_reason, :created_at, :updated_at
                )
                """,
                asdict(context),
            )
        return context

    def _get_sync(
        self, connection: sqlite3.Connection, context_id: str
    ) -> WorkContextRecord | None:
        row = connection.execute(
            "SELECT * FROM work_contexts WHERE id = ?", (context_id,)
        ).fetchone()
        return WorkContextRecord.from_row(row) if row else None

    def _get_by_job_sync(
        self, connection: sqlite3.Connection, job_id: str
    ) -> WorkContextRecord | None:
        row = connection.execute(
            "SELECT * FROM work_contexts WHERE job_id = ?", (job_id,)
        ).fetchone()
        return WorkContextRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[WorkContextRecord]:
        rows = connection.execute("SELECT * FROM work_contexts ORDER BY created_at, id").fetchall()
        return [WorkContextRecord.from_row(row) for row in rows]

    def _list_by_session_sync(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[WorkContextRecord]:
        rows = connection.execute(
            "SELECT * FROM work_contexts WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        return [WorkContextRecord.from_row(row) for row in rows]

    def _list_by_pool_sync(
        self,
        connection: sqlite3.Connection,
        runtime_pool_id: str,
    ) -> list[WorkContextRecord]:
        rows = connection.execute(
            "SELECT * FROM work_contexts WHERE runtime_pool_id = ? ORDER BY created_at, id",
            (runtime_pool_id,),
        ).fetchall()
        return [WorkContextRecord.from_row(row) for row in rows]

    def _list_by_agent_sync(
        self,
        connection: sqlite3.Connection,
        agent_id: str,
    ) -> list[WorkContextRecord]:
        rows = connection.execute(
            "SELECT * FROM work_contexts WHERE agent_id = ? ORDER BY created_at, id",
            (agent_id,),
        ).fetchall()
        return [WorkContextRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        context: WorkContextRecord,
    ) -> WorkContextRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE work_contexts SET
                    session_id = :session_id,
                    job_id = :job_id,
                    agent_id = :agent_id,
                    runtime_pool_id = :runtime_pool_id,
                    runtime_id = :runtime_id,
                    context_key = :context_key,
                    workspace_path = :workspace_path,
                    isolation_mode = :isolation_mode,
                    context_status = :context_status,
                    ownership_state = :ownership_state,
                    selection_reason = :selection_reason,
                    failure_reason = :failure_reason,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(context),
            )
        if result.rowcount == 0:
            raise LookupError(f"Work context not found: {context.id}")
        return context
