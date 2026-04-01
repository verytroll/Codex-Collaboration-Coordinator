"""Deployment readiness checks for startup and external probes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.db.connection import connect_sqlite
from app.db.migrations.runner import (
    DEFAULT_MIGRATIONS_DIR,
    MIGRATION_TABLE_NAME,
    list_migration_files,
    load_applied_migrations,
)


class DeploymentReadinessService:
    """Check whether the coordinator is ready for external traffic."""

    def __init__(
        self,
        *,
        database_url: str,
        migrations_dir: Path | None = None,
    ) -> None:
        self.database_url = database_url
        self.migrations_dir = migrations_dir or DEFAULT_MIGRATIONS_DIR

    async def get_readiness(self) -> dict[str, Any]:
        """Return a readiness payload for the deployment surface."""
        db_check = await self._check_database()
        if db_check["status"] != "ok":
            return {
                "status": "unavailable",
                "checks": {
                    "db": db_check,
                    "migrations": {
                        "status": "unavailable",
                        "detail": (
                            "Migration verification skipped because the database is unavailable."
                        ),
                    },
                },
            }

        migration_check = await self._check_migrations()
        return {
            "status": migration_check["status"],
            "checks": {
                "db": db_check,
                "migrations": migration_check,
            },
        }

    async def _check_database(self) -> dict[str, str]:
        try:
            await asyncio.to_thread(self._probe_database_sync)
        except Exception as exc:
            return {"status": "unavailable", "detail": f"Database check failed: {exc}"}
        return {"status": "ok", "detail": "SQLite reachable."}

    def _probe_database_sync(self) -> None:
        connection = connect_sqlite(self.database_url)
        try:
            connection.execute("SELECT 1").fetchone()
        finally:
            connection.close()

    async def _check_migrations(self) -> dict[str, str]:
        try:
            await asyncio.to_thread(self._probe_migrations_sync)
        except Exception as exc:
            return {"status": "unavailable", "detail": f"Migration check failed: {exc}"}
        migration_count = len(list_migration_files(self.migrations_dir))
        return {
            "status": "ok",
            "detail": f"{migration_count} migration(s) applied and verified.",
        }

    def _probe_migrations_sync(self) -> None:
        connection = connect_sqlite(self.database_url)
        try:
            table_exists = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (MIGRATION_TABLE_NAME,),
            ).fetchone()
            if table_exists is None:
                raise RuntimeError("Migration tracking table is missing")

            applied = load_applied_migrations(connection)
            migrations = list_migration_files(self.migrations_dir)
            migration_by_name = {migration.path.name: migration for migration in migrations}

            missing = [
                migration.path.name
                for migration in migrations
                if migration.path.name not in applied
            ]
            extra = sorted(version for version in applied if version not in migration_by_name)
            if missing:
                raise RuntimeError(f"Pending migration(s): {', '.join(missing)}")
            if extra:
                raise RuntimeError(f"Unknown migration(s) recorded in database: {', '.join(extra)}")

            for migration in migrations:
                applied_migration = applied[migration.path.name]
                if applied_migration.checksum != migration.checksum:
                    raise RuntimeError(
                        f"Migration checksum mismatch for {migration.path.name}: "
                        f"database={applied_migration.checksum} file={migration.checksum}"
                    )
        finally:
            connection.close()
