"""Integration principal and credential repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from app.repositories._base import SQLiteRepositoryBase


@dataclass(frozen=True, slots=True)
class IntegrationPrincipalRecord:
    """Integration principal row."""

    id: str
    display_label: str
    principal_type: str
    actor_role: str
    actor_type: str
    source: str
    default_scopes_json: str
    notes: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "IntegrationPrincipalRecord":
        return cls(
            id=row["id"],
            display_label=row["display_label"],
            principal_type=row["principal_type"],
            actor_role=row["actor_role"],
            actor_type=row["actor_type"],
            source=row["source"],
            default_scopes_json=row["default_scopes_json"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True, slots=True)
class IntegrationCredentialRecord:
    """Integration credential row."""

    id: str
    principal_id: str
    label: str
    secret_hash: str
    secret_prefix: str
    scopes_json: str
    status: str
    status_reason: str | None
    status_note: str | None
    expires_at: str | None
    revoked_at: str | None
    last_used_at: str | None
    last_used_surface: str | None
    notes: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "IntegrationCredentialRecord":
        return cls(
            id=row["id"],
            principal_id=row["principal_id"],
            label=row["label"],
            secret_hash=row["secret_hash"],
            secret_prefix=row["secret_prefix"],
            scopes_json=row["scopes_json"],
            status=row["status"],
            status_reason=row["status_reason"],
            status_note=row["status_note"],
            expires_at=row["expires_at"],
            revoked_at=row["revoked_at"],
            last_used_at=row["last_used_at"],
            last_used_surface=row["last_used_surface"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class IntegrationPrincipalRepository(SQLiteRepositoryBase):
    """CRUD access for integration principals."""

    async def create(self, principal: IntegrationPrincipalRecord) -> IntegrationPrincipalRecord:
        return await self._run(lambda connection: self._create_sync(connection, principal))

    async def get(self, principal_id: str) -> IntegrationPrincipalRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, principal_id))

    async def list(self) -> list[IntegrationPrincipalRecord]:
        return await self._run(self._list_sync)

    async def update(self, principal: IntegrationPrincipalRecord) -> IntegrationPrincipalRecord:
        return await self._run(lambda connection: self._update_sync(connection, principal))

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        principal: IntegrationPrincipalRecord,
    ) -> IntegrationPrincipalRecord:
        with connection:
            connection.execute(
                """
                INSERT INTO integration_principals (
                    id, display_label, principal_type, actor_role, actor_type,
                    source, default_scopes_json, notes, created_at, updated_at
                ) VALUES (
                    :id, :display_label, :principal_type, :actor_role, :actor_type,
                    :source, :default_scopes_json, :notes, :created_at, :updated_at
                )
                """,
                asdict(principal),
            )
        return principal

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        principal_id: str,
    ) -> IntegrationPrincipalRecord | None:
        row = connection.execute(
            "SELECT * FROM integration_principals WHERE id = ?",
            (principal_id,),
        ).fetchone()
        return IntegrationPrincipalRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[IntegrationPrincipalRecord]:
        rows = connection.execute(
            "SELECT * FROM integration_principals ORDER BY created_at, id"
        ).fetchall()
        return [IntegrationPrincipalRecord.from_row(row) for row in rows]

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        principal: IntegrationPrincipalRecord,
    ) -> IntegrationPrincipalRecord:
        with connection:
            result = connection.execute(
                """
                UPDATE integration_principals SET
                    display_label = :display_label,
                    principal_type = :principal_type,
                    actor_role = :actor_role,
                    actor_type = :actor_type,
                    source = :source,
                    default_scopes_json = :default_scopes_json,
                    notes = :notes,
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                asdict(principal),
            )
        if result.rowcount == 0:
            raise LookupError(f"Integration principal not found: {principal.id}")
        return principal


class IntegrationCredentialRepository(SQLiteRepositoryBase):
    """CRUD access for integration credentials."""

    async def create(self, credential: IntegrationCredentialRecord) -> IntegrationCredentialRecord:
        return await self._run(lambda connection: self._create_sync(connection, credential))

    async def get(self, credential_id: str) -> IntegrationCredentialRecord | None:
        return await self._run(lambda connection: self._get_sync(connection, credential_id))

    async def list(self) -> list[IntegrationCredentialRecord]:
        return await self._run(self._list_sync)

    async def list_by_principal(self, principal_id: str) -> list[IntegrationCredentialRecord]:
        return await self._run(
            lambda connection: self._list_by_principal_sync(connection, principal_id)
        )

    async def get_by_secret_hash(self, secret_hash: str) -> IntegrationCredentialRecord | None:
        return await self._run(
            lambda connection: self._get_by_secret_hash_sync(connection, secret_hash)
        )

    async def update(self, credential: IntegrationCredentialRecord) -> IntegrationCredentialRecord:
        return await self._run(lambda connection: self._update_sync(connection, credential))

    async def rotate(
        self,
        *,
        revoked: IntegrationCredentialRecord,
        replacement: IntegrationCredentialRecord,
    ) -> IntegrationCredentialRecord:
        return await self._run(
            lambda connection: self._rotate_sync(connection, revoked, replacement)
        )

    def _create_sync(
        self,
        connection: sqlite3.Connection,
        credential: IntegrationCredentialRecord,
    ) -> IntegrationCredentialRecord:
        with connection:
            self._insert_row(connection, credential)
        return credential

    def _get_sync(
        self,
        connection: sqlite3.Connection,
        credential_id: str,
    ) -> IntegrationCredentialRecord | None:
        row = connection.execute(
            "SELECT * FROM integration_credentials WHERE id = ?",
            (credential_id,),
        ).fetchone()
        return IntegrationCredentialRecord.from_row(row) if row else None

    def _list_sync(self, connection: sqlite3.Connection) -> list[IntegrationCredentialRecord]:
        rows = connection.execute(
            "SELECT * FROM integration_credentials ORDER BY created_at, id"
        ).fetchall()
        return [IntegrationCredentialRecord.from_row(row) for row in rows]

    def _list_by_principal_sync(
        self,
        connection: sqlite3.Connection,
        principal_id: str,
    ) -> list[IntegrationCredentialRecord]:
        rows = connection.execute(
            """
            SELECT * FROM integration_credentials
            WHERE principal_id = ?
            ORDER BY created_at, id
            """,
            (principal_id,),
        ).fetchall()
        return [IntegrationCredentialRecord.from_row(row) for row in rows]

    def _get_by_secret_hash_sync(
        self,
        connection: sqlite3.Connection,
        secret_hash: str,
    ) -> IntegrationCredentialRecord | None:
        row = connection.execute(
            "SELECT * FROM integration_credentials WHERE secret_hash = ?",
            (secret_hash,),
        ).fetchone()
        return IntegrationCredentialRecord.from_row(row) if row else None

    def _update_sync(
        self,
        connection: sqlite3.Connection,
        credential: IntegrationCredentialRecord,
    ) -> IntegrationCredentialRecord:
        with connection:
            result = self._update_row(connection, credential)
        if result.rowcount == 0:
            raise LookupError(f"Integration credential not found: {credential.id}")
        return credential

    def _rotate_sync(
        self,
        connection: sqlite3.Connection,
        revoked: IntegrationCredentialRecord,
        replacement: IntegrationCredentialRecord,
    ) -> IntegrationCredentialRecord:
        with connection:
            result = self._update_row(connection, revoked)
            if result.rowcount == 0:
                raise LookupError(f"Integration credential not found: {revoked.id}")
            self._insert_row(connection, replacement)
        return replacement

    def _insert_row(
        self,
        connection: sqlite3.Connection,
        credential: IntegrationCredentialRecord,
    ) -> None:
        connection.execute(
            """
            INSERT INTO integration_credentials (
                id, principal_id, label, secret_hash, secret_prefix, scopes_json,
                status, status_reason, status_note, expires_at, revoked_at,
                last_used_at, last_used_surface, notes, created_at, updated_at
            ) VALUES (
                :id, :principal_id, :label, :secret_hash, :secret_prefix, :scopes_json,
                :status, :status_reason, :status_note, :expires_at, :revoked_at,
                :last_used_at, :last_used_surface, :notes, :created_at, :updated_at
            )
            """,
            asdict(credential),
        )

    def _update_row(
        self,
        connection: sqlite3.Connection,
        credential: IntegrationCredentialRecord,
    ) -> sqlite3.Cursor:
        return connection.execute(
            """
            UPDATE integration_credentials SET
                principal_id = :principal_id,
                label = :label,
                secret_hash = :secret_hash,
                secret_prefix = :secret_prefix,
                scopes_json = :scopes_json,
                status = :status,
                status_reason = :status_reason,
                status_note = :status_note,
                expires_at = :expires_at,
                revoked_at = :revoked_at,
                last_used_at = :last_used_at,
                last_used_surface = :last_used_surface,
                notes = :notes,
                created_at = :created_at,
                updated_at = :updated_at
            WHERE id = :id
            """,
            asdict(credential),
        )
