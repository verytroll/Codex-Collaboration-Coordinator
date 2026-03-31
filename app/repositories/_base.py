"""Shared SQLite repository helpers."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable
from typing import TypeVar

from app.db.connection import connect_sqlite

T = TypeVar("T")


class SQLiteRepositoryBase:
    """Base class for async repositories backed by SQLite."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    async def _run(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        """Run a synchronous SQLite operation in a worker thread."""
        return await asyncio.to_thread(self._run_sync, operation)

    def _run_sync(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        """Run a SQLite operation inside a managed connection."""
        connection = connect_sqlite(self.database_url)
        try:
            return operation(connection)
        finally:
            connection.close()
