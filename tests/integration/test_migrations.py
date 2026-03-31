from __future__ import annotations

import asyncio
import sqlite3

from app.db.connection import connect_sqlite
from app.db.migrations import DEFAULT_MIGRATIONS_DIR, MIGRATION_TABLE_NAME, migrate_sqlite


def test_connect_sqlite_creates_parent_directory_and_enables_foreign_keys(tmp_path) -> None:
    database_path = tmp_path / "nested" / "coordinator.db"
    connection = connect_sqlite(f"sqlite:///{database_path.as_posix()}")
    try:
        assert database_path.parent.is_dir()
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        connection.close()


def test_migrate_sqlite_applies_each_file_only_once(tmp_path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_create_example.sql").write_text(
        """
        CREATE TABLE example (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        """.strip(),
        encoding="utf-8",
    )
    database_path = tmp_path / "coordinator.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    first_run = asyncio.run(migrate_sqlite(database_url, migrations_dir=migrations_dir))
    second_run = asyncio.run(migrate_sqlite(database_url, migrations_dir=migrations_dir))

    assert first_run == ["001_create_example.sql"]
    assert second_run == []

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        version_count = connection.execute(
            f"SELECT COUNT(*) FROM {MIGRATION_TABLE_NAME}"
        ).fetchone()[0]

    assert MIGRATION_TABLE_NAME in tables
    assert "example" in tables
    assert version_count == 1


def test_migrate_sqlite_applies_baseline_schema(tmp_path) -> None:
    database_path = tmp_path / "baseline.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    first_run = asyncio.run(
        migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR)
    )
    second_run = asyncio.run(
        migrate_sqlite(database_url, migrations_dir=DEFAULT_MIGRATIONS_DIR)
    )

    assert first_run == ["001_baseline_tables.sql", "002_baseline_indexes.sql"]
    assert second_run == []

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        indexes = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
        version_count = connection.execute(
            f"SELECT COUNT(*) FROM {MIGRATION_TABLE_NAME}"
        ).fetchone()[0]

    assert {"agents", "agent_runtimes", "sessions", "session_participants"}.issubset(tables)
    assert {
        "idx_sessions_lead_agent_id",
        "idx_agent_runtimes_agent_id",
        "idx_session_participants_session_id",
        "idx_session_participants_agent_id",
    }.issubset(indexes)
    assert version_count == 2
