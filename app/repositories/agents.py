"""Agent and runtime repositories."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import sqlite3

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class AgentRecord:
    """Agent row."""

    id: str
    display_name: str
    role: str
    is_lead_default: int
    runtime_kind: str
    capabilities_json: str | None
    default_config_json: str | None
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AgentRecord":
        return cls(
            id=row["id"],
            display_name=row["display_name"],
            role=row["role"],
            is_lead_default=row["is_lead_default"],
            runtime_kind=row["runtime_kind"],
            capabilities_json=row["capabilities_json"],
            default_config_json=row["default_config_json"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True, slots=True)
class AgentRuntimeRecord:
    """Agent runtime row."""

    id: str
    agent_id: str
    runtime_kind: str
    transport_kind: str
    transport_config_json: str | None
    workspace_path: str | None
    approval_policy: str | None
    sandbox_policy: str | None
    runtime_status: str
    last_heartbeat_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AgentRuntimeRecord":
        return cls(
            id=row["id"],
            agent_id=row["agent_id"],
            runtime_kind=row["runtime_kind"],
            transport_kind=row["transport_kind"],
            transport_config_json=row["transport_config_json"],
            workspace_path=row["workspace_path"],
            approval_policy=row["approval_policy"],
            sandbox_policy=row["sandbox_policy"],
            runtime_status=row["runtime_status"],
            last_heartbeat_at=row["last_heartbeat_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class AgentRepository(SQLiteRepositoryBase):
    """CRUD access for agents."""

    async def create(self, agent: AgentRecord) -> AgentRecord:
        return await self._run(lambda connection: self._create_sync(connection, agent))

    async def get(self, agent_id: str) -> AgentRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, agent_id))

    async def list(self) -> list[AgentRecord]:
        return await self._run(self._list_sync)

    async def update(self, agent: AgentRecord) -> AgentRecord:
        return await self._run(lambda connection: self._update_sync(connection, agent))

    async def delete(self, agent_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, agent_id))

    def _create_sync(self, connection: sqlite3.Connection, agent: AgentRecord) -> AgentRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO agents (
                    id, display_name, role, is_lead_default, runtime_kind,
                    capabilities_json, default_config_json, status,
                    created_at, updated_at
                ) VALUES (
                    :id, :display_name, :role, :is_lead_default, :runtime_kind,
                    :capabilities_json, :default_config_json, :status,
                    :created_at, :updated_at
                )
                """,
                asdict(agent),
            )
        return agent

    def _get_sync(self, connection: sqlite3.Connection, agent_id: str) -> AgentRecord | None:
        row = connection.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return AgentRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[AgentRecord]:
        rows = connection.execute("SELECT * FROM agents ORDER BY display_name, id").fetchall()
        return [AgentRecord.from_row(row) for row in rows]

    def _update_sync(self, connection: sqlite3.Connection, agent: AgentRecord) -> AgentRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE agents SET
                    display_name = :display_name,
                    role = :role,
                    is_lead_default = :is_lead_default,
                    runtime_kind = :runtime_kind,
                    capabilities_json = :capabilities_json,
                    default_config_json = :default_config_json,
                    status = :status,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(agent),
            )
        if result.rowcount == 0:
            raise LookupError(f"Agent not found: {agent.id}")
        return agent

    def _delete_sync(self, connection: sqlite3.Connection, agent_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        return result.rowcount > 0


class AgentRuntimeRepository(SQLiteRepositoryBase):
    """CRUD access for agent runtimes."""

    async def create(self, runtime: AgentRuntimeRecord) -> AgentRuntimeRecord:
        return await self._run(lambda connection: self._create_sync(connection, runtime))

    async def get(self, runtime_id: str) -> AgentRuntimeRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, runtime_id))

    async def list(self) -> list[AgentRuntimeRecord]:
        return await self._run(self._list_sync)

    async def update(self, runtime: AgentRuntimeRecord) -> AgentRuntimeRecord:
        return await self._run(lambda connection: self._update_sync(connection, runtime))

    async def delete(self, runtime_id: str) -> bool:
        return await self._run(lambda connection: self._delete_sync(connection, runtime_id))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        runtime: AgentRuntimeRecord,
    ) -> AgentRuntimeRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO agent_runtimes (
                    id, agent_id, runtime_kind, transport_kind, transport_config_json,
                    workspace_path, approval_policy, sandbox_policy, runtime_status,
                    last_heartbeat_at, created_at, updated_at
                ) VALUES (
                    :id, :agent_id, :runtime_kind, :transport_kind, :transport_config_json,
                    :workspace_path, :approval_policy, :sandbox_policy, :runtime_status,
                    :last_heartbeat_at, :created_at, :updated_at
                )
                """,
                asdict(runtime),
            )
        return runtime

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        runtime_id: str,
    ) -> AgentRuntimeRecord | None:
        row = connection.execute(
            "SELECT * FROM agent_runtimes WHERE id = ?",
            (runtime_id,),
        ).fetchone()
        return AgentRuntimeRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[AgentRuntimeRecord]:
        rows = connection.execute("SELECT * FROM agent_runtimes ORDER BY created_at, id").fetchall()
        return [AgentRuntimeRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        runtime: AgentRuntimeRecord,
    ) -> AgentRuntimeRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE agent_runtimes SET
                    agent_id = :agent_id,
                    runtime_kind = :runtime_kind,
                    transport_kind = :transport_kind,
                    transport_config_json = :transport_config_json,
                    workspace_path = :workspace_path,
                    approval_policy = :approval_policy,
                    sandbox_policy = :sandbox_policy,
                    runtime_status = :runtime_status,
                    last_heartbeat_at = :last_heartbeat_at,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(runtime),
            )
        if result.rowcount == 0:
            raise LookupError(f"Agent runtime not found: {runtime.id}")
        return runtime

    def _delete_sync(self, connection: sqlite3.Connection, runtime_id: str) -> bool:
        with connection:
            result = connection.execute("DELETE FROM agent_runtimes WHERE id = ?", (runtime_id,))
        return result.rowcount > 0
