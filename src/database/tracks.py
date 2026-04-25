from __future__ import annotations

from pathlib import Path

from src.data_loading import get_events_with_available_laps, get_schedule_events


class F1TrackQuery:
    """
    FastF1-backed query helper for track/event metadata.

    Reads from the FastF1 schedule or the local cache directory rather than
    the local SQLite DB.  Use TrackRepository for DB-persisted event records.

    Pattern: Query Object / Static Helper
    """

    @staticmethod
    def from_schedule(year: int) -> list[str]:
        """Return all scheduled tracks (event names) for a season."""
        return get_schedule_events(year)

    @staticmethod
    def with_lap_data(
        year: int,
        session_code: str,
        *,
        cache_dir: str | Path = "cache",
    ) -> list[str]:
        """Return tracks for which lap data can actually be loaded."""
        return get_events_with_available_laps(
            year=year,
            session_code=session_code,
            cache_dir=cache_dir,
        )
