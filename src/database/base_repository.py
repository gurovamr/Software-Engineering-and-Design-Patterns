import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Iterator


class BaseRepository(ABC):
    """
    Abstract base class for all repositories.

    Provides a shared, safe database connection context manager.
    Subclasses define domain-specific query methods.

    Pattern: Repository (Abstract Base)
    Principle: Dependency Inversion, Open/Closed
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Opens a SQLite connection, commits on success, always closes."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
