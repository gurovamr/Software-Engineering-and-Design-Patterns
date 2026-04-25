from __future__ import annotations

import sqlite3
from abc import ABC
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class BaseRepository(ABC):
    """
    Abstract base class for all repositories.

    Provides a shared, safe database connection context manager.
    Subclasses define domain-specific query methods.

    Pattern: Repository (Abstract Base)
    Principle: Dependency Inversion, Open/Closed
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Opens a SQLite connection, commits on success, always closes."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
