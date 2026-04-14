import json

from src.database.base_repository import BaseRepository


class SyncRepository(BaseRepository):
    """
    Handles all sync_state database operations for the data preloading service.

    Responsibilities:
    - Ensure sync_state schema is up to date
    - Read sync state per year
    - Write/update sync state per year
    - Mark a year as fully synced

    Pattern: Repository
    Principle: SRP – extracted from DataLoader to isolate DB concerns
    """

    def ensure_schema(self) -> None:
        """Adds synced_events_json column to sync_state if missing."""
        with self._connect() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(sync_state)").fetchall()}
            if "synced_events_json" not in cols:
                try:
                    conn.execute(
                        "ALTER TABLE sync_state ADD COLUMN synced_events_json TEXT DEFAULT '[]'"
                    )
                except Exception:
                    pass

    def get_state(self, year: int) -> dict | None:
        """
        Returns the sync state for a given year, or None if not recorded.

        Returns a dict with keys: 'complete' (bool), 'synced_keys' (list[str])
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT complete, synced_events_json FROM sync_state WHERE year = ?",
                (year,),
            ).fetchone()
        if row is None:
            return None
        return {
            "complete": bool(row[0]),
            "synced_keys": json.loads(row[1]) if row[1] else [],
        }

    def save_state(self, year: int, keys: list[str], complete: bool) -> None:
        """Inserts or updates the sync state for a given year."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_state
                    (year, session_codes_json, synced_events_json, complete, last_sync_at)
                VALUES (?, '[]', ?, ?, datetime('now'))
                ON CONFLICT(year) DO UPDATE SET
                    synced_events_json = excluded.synced_events_json,
                    complete           = excluded.complete,
                    last_sync_at       = excluded.last_sync_at
                """,
                (year, json.dumps(keys), int(complete)),
            )

    def mark_complete(self, year: int, keys: list[str]) -> None:
        """Marks a year as fully synced."""
        self.save_state(year, keys, complete=True)
