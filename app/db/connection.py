"""SQLite connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def normalize_sqlite_path(database_url: str) -> str:
    """Convert a SQLite URL or path into a local filesystem path."""
    if database_url == ":memory:":
        return database_url

    if database_url.startswith("sqlite:///"):
        raw_path = database_url.removeprefix("sqlite:///")
    elif database_url.startswith("sqlite://"):
        raw_path = database_url.removeprefix("sqlite://")
    else:
        raw_path = database_url

    if raw_path in {":memory:", "/:memory:"}:
        return ":memory:"

    if len(raw_path) >= 3 and raw_path.startswith("/") and raw_path[2] == ":":
        return raw_path.lstrip("/")

    return raw_path


def connect_sqlite(database_url: str) -> sqlite3.Connection:
    """Create a SQLite connection from a SQLite URL or file path."""
    database_path = normalize_sqlite_path(database_url)
    if database_path != ":memory:":
        Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection
