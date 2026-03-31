"""SQLite migration runner."""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.db.connection import connect_sqlite

MIGRATION_TABLE_NAME = "schema_migrations"
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class MigrationFile:
    """A SQL migration file discovered on disk."""

    path: Path
    checksum: str


def ensure_migration_table(connection: sqlite3.Connection) -> None:
    """Create the migration tracking table if it does not exist."""
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE_NAME} (
            version TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def list_migration_files(migrations_dir: Path) -> list[MigrationFile]:
    """Return sorted SQL migration files from the given directory."""
    if not migrations_dir.exists():
        return []

    files = [path for path in migrations_dir.iterdir() if path.is_file() and path.suffix == ".sql"]
    return [
        MigrationFile(path=file_path, checksum=hashlib.sha256(file_path.read_bytes()).hexdigest())
        for file_path in sorted(files)
    ]


def load_applied_versions(connection: sqlite3.Connection) -> set[str]:
    """Read already applied migration versions."""
    rows = connection.execute(f"SELECT version FROM {MIGRATION_TABLE_NAME}").fetchall()
    return {row["version"] for row in rows}


def apply_migration(connection: sqlite3.Connection, migration: MigrationFile) -> None:
    """Execute a single migration and record it."""
    sql = migration.path.read_text(encoding="utf-8")
    with connection:
        connection.executescript(sql)
        connection.execute(
            f"""
            INSERT INTO {MIGRATION_TABLE_NAME} (version, filename, checksum)
            VALUES (?, ?, ?)
            """,
            (migration.path.name, migration.path.name, migration.checksum),
        )


def migrate_sqlite_sync(
    database_url: str,
    migrations_dir: Path | None = None,
) -> list[str]:
    """Apply pending migrations synchronously."""
    migration_dir = migrations_dir or DEFAULT_MIGRATIONS_DIR
    connection = connect_sqlite(database_url)
    try:
        ensure_migration_table(connection)
        applied_versions = load_applied_versions(connection)
        applied_now: list[str] = []
        for migration in list_migration_files(migration_dir):
            if migration.path.name in applied_versions:
                continue
            apply_migration(connection, migration)
            applied_now.append(migration.path.name)
        return applied_now
    finally:
        connection.close()


async def migrate_sqlite(
    database_url: str,
    migrations_dir: Path | None = None,
) -> list[str]:
    """Apply pending migrations without blocking the event loop."""
    return await asyncio.to_thread(migrate_sqlite_sync, database_url, migrations_dir)
