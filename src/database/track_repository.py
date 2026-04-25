from __future__ import annotations

from src.database.base_repository import BaseRepository


class TrackRepository(BaseRepository):
    """
    SQLite-backed store for F1 track/event metadata.

    Responsibilities:
    - Create and migrate the tracks schema
    - Persist event names per season (upsert — safe to re-run on updates)
    - Retrieve cached event lists without any network access

    Pattern: Repository
    Principle: Single Responsibility, local-cache-first
    """

    def ensure_schema(self) -> None:
        """Creates the tracks table if it does not already exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tracks (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    year         INTEGER NOT NULL,
                    round_number INTEGER,
                    event_name   TEXT    NOT NULL,
                    country      TEXT,
                    circuit_key  TEXT,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, event_name)
                )
                """
            )

    def get_events(self, year: int) -> list[str]:
        """Returns all cached event names for a season, ordered by round number."""
        self.ensure_schema()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_name FROM tracks
                WHERE year = ?
                ORDER BY round_number, event_name
                """,
                (year,),
            ).fetchall()
        return [row[0] for row in rows]

    def upsert_events(self, year: int, events: list[dict]) -> None:
        """
        Insert or update events for a season.

        Each dict must contain 'event_name' and may optionally include
        'round_number', 'country', and 'circuit_key'.
        """
        self.ensure_schema()
        with self._connect() as conn:
            for ev in events:
                if "event_name" not in ev:
                    raise ValueError(f"Each event dict must contain 'event_name', got: {ev!r}")
                conn.execute(
                    """
                    INSERT INTO tracks
                        (year, round_number, event_name, country, circuit_key, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(year, event_name) DO UPDATE SET
                        round_number = excluded.round_number,
                        country      = excluded.country,
                        circuit_key  = excluded.circuit_key,
                        updated_at   = excluded.updated_at
                    """,
                    (
                        year,
                        ev.get("round_number"),
                        ev["event_name"],
                        ev.get("country"),
                        ev.get("circuit_key"),
                    ),
                )

    def upsert_event_names(self, year: int, event_names: list[str]) -> None:
        """Convenience wrapper: upsert from a plain list of event name strings."""
        self.upsert_events(year, [{"event_name": name} for name in event_names])
