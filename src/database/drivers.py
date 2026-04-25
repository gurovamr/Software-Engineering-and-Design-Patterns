from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_loading import load_f1_data


class Drivers:
    """Access helper for driver-related data used by the app/UI layer."""

    @staticmethod
    def from_laps(laps_df: pd.DataFrame) -> list[str]:
        """Extract a sorted, unique driver list from a laps table."""
        if laps_df.empty or "Driver" not in laps_df.columns:
            return []

        drivers = laps_df["Driver"].dropna().astype(str).str.strip()
        drivers = drivers[drivers != ""]
        return sorted(drivers.unique().tolist())

    @staticmethod
    def from_results(results_df: pd.DataFrame) -> list[str]:
        """Extract a sorted, unique driver list from a results table."""
        if results_df.empty:
            return []

        for column in ["Driver", "Abbreviation", "BroadcastName", "FullName"]:
            if column in results_df.columns:
                values = results_df[column].dropna().astype(str).str.strip()
                values = values[values != ""]
                if not values.empty:
                    return sorted(values.unique().tolist())

        return []

    @classmethod
    def for_session(
        cls,
        year: int,
        event: str | int,
        session_code: str,
        *,
        cache_dir: str | Path = "cache",
    ) -> list[str]:
        """Return drivers available in a specific session."""
        bundle = load_f1_data(
            year=year,
            event=event,
            session_code=session_code,
            cache_dir=cache_dir,
            include_weather=False,
            include_messages=False,
            add_distance=False,
        )

        result_drivers = cls.from_results(bundle.results)
        if result_drivers:
            return result_drivers

        return cls.from_laps(bundle.laps)
