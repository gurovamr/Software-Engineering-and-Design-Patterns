from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterable

import pandas as pd
import fastf1


# -----------------------------
# Request / Response Data Types
# -----------------------------

@dataclass(frozen=True)
class SessionRequest:
    year: int
    event: str | int
    session_code: str  # e.g. "R", "Q", "FP1", "FP2", "S"
    drivers: Optional[list[str]] = None
    fastest_lap_only: bool = False
    include_weather: bool = True
    include_messages: bool = False
    add_distance: bool = True


@dataclass
class TelemetryBundle:
    session_info: dict
    results: pd.DataFrame
    laps: pd.DataFrame
    weather: pd.DataFrame
    telemetry: pd.DataFrame
    track_status: pd.DataFrame
    session_status: pd.DataFrame
    race_control_messages: pd.DataFrame

    def save(self, output_dir: str | Path) -> None:
        """
        Save all normalized tables to parquet files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.results.to_parquet(output_dir / "results.parquet", index=False)
        self.laps.to_parquet(output_dir / "laps.parquet", index=False)
        self.weather.to_parquet(output_dir / "weather.parquet", index=False)
        self.telemetry.to_parquet(output_dir / "telemetry.parquet", index=False)
        self.track_status.to_parquet(output_dir / "track_status.parquet", index=False)
        self.session_status.to_parquet(output_dir / "session_status.parquet", index=False)
        self.race_control_messages.to_parquet(
            output_dir / "race_control_messages.parquet", index=False
        )


# -----------------------------
# Abstraction
# -----------------------------

class TelemetrySource(ABC):
    @abstractmethod
    def load_bundle(self, request: SessionRequest) -> TelemetryBundle:
        raise NotImplementedError


# -----------------------------
# FastF1 Adapter
# -----------------------------

class FastF1Source(TelemetrySource):
    """
    Adapter around FastF1.

    Responsibilities:
    - enable caching
    - load a session
    - normalize session/lap/telemetry data into project-friendly tables

    This keeps notebook/app code independent from FastF1 internals.
    """

    def __init__(self, cache_dir: str | Path = "cache") -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(self._cache_dir))

    @staticmethod
    def _safe_copy_session_attr(session, attr_name: str) -> pd.DataFrame:
        try:
            value = getattr(session, attr_name)
            if value is None:
                return pd.DataFrame()
            return value.copy()
        except Exception:
            return pd.DataFrame()

    def load_bundle(self, request: SessionRequest) -> TelemetryBundle:
        session = fastf1.get_session(
            request.year,
            request.event,
            request.session_code
        )

        session.load(
            laps=True,
            telemetry=True,
            weather=request.include_weather,
            messages=request.include_messages
        )

        results_df = self._prepare_results(session)
        laps_df = self._prepare_laps(session)
        telemetry_df = self._prepare_telemetry(
            session=session,
            laps_df=laps_df,
            drivers=request.drivers,
            fastest_lap_only=request.fastest_lap_only,
            add_distance=request.add_distance
        )

        weather_df = self._safe_copy_session_attr(session, "weather_data")
        track_status_df = self._safe_copy_session_attr(session, "track_status")
        session_status_df = self._safe_copy_session_attr(session, "session_status")
        race_control_df = self._safe_copy_session_attr(session, "race_control_messages")

        return TelemetryBundle(
            session_info=dict(session.session_info),
            results=results_df.reset_index(drop=True),
            laps=laps_df.reset_index(drop=True),
            weather=weather_df.reset_index(drop=True),
            telemetry=telemetry_df.reset_index(drop=True),
            track_status=track_status_df.reset_index(drop=True),
            session_status=session_status_df.reset_index(drop=True),
            race_control_messages=race_control_df.reset_index(drop=True)
        )

    @staticmethod
    def _prepare_results(session) -> pd.DataFrame:
        try:
            results = session.results.copy()
        except Exception:
            return pd.DataFrame()

        # Normalize some useful names for downstream plotting / API use
        rename_map = {
            "Abbreviation": "Driver",
            "TeamName": "Team",
            "Position": "FinishPosition",
            "GridPosition": "GridPosition",
            "Time": "ResultTime"
        }
        existing = {k: v for k, v in rename_map.items() if k in results.columns}
        results = results.rename(columns=existing)

        results["EventName"] = session.event["EventName"]
        results["Year"] = session.event["EventDate"].year if "EventDate" in session.event else None
        results["SessionName"] = session.name
        return results

    @staticmethod
    def _prepare_laps(session) -> pd.DataFrame:
        try:
            laps = session.laps.copy()
        except Exception:
            return pd.DataFrame()

        # Timedelta columns -> seconds where useful
        timedelta_cols = [
            "LapTime", "Sector1Time", "Sector2Time", "Sector3Time",
            "PitInTime", "PitOutTime"
        ]
        for col in timedelta_cols:
            if col in laps.columns:
                laps[f"{col}Seconds"] = laps[col].dt.total_seconds()

        laps["EventName"] = session.event["EventName"]
        laps["SessionName"] = session.name

        return laps

    def _prepare_telemetry(
        self,
        session,
        laps_df: pd.DataFrame,
        drivers: Optional[Iterable[str]],
        fastest_lap_only: bool,
        add_distance: bool
    ) -> pd.DataFrame:
        if laps_df.empty:
            return pd.DataFrame()

        try:
            session_laps = session.laps
        except Exception:
            return pd.DataFrame()

        available_drivers = sorted(laps_df["Driver"].dropna().unique().tolist())
        selected_drivers = list(drivers) if drivers else available_drivers

        telemetry_frames: list[pd.DataFrame] = []

        for driver in selected_drivers:
            driver_laps = session_laps[session_laps["Driver"] == driver]
            if driver_laps.empty:
                continue

            if fastest_lap_only:
                lap_candidates = [driver_laps.pick_fastest()]
            else:
                lap_candidates = [lap for _, lap in driver_laps.iterlaps()]

            for lap in lap_candidates:
                lap_frame = self._build_single_lap_telemetry(
                    session=session,
                    lap=lap,
                    add_distance=add_distance
                )
                if not lap_frame.empty:
                    telemetry_frames.append(lap_frame)

        if not telemetry_frames:
            return pd.DataFrame()

        telemetry = pd.concat(telemetry_frames, ignore_index=True)

        # Optional convenience columns for plotting
        if "Time" in telemetry.columns:
            telemetry["TimeSeconds"] = telemetry["Time"].dt.total_seconds()

        if "SessionTime" in telemetry.columns:
            telemetry["SessionTimeSeconds"] = telemetry["SessionTime"].dt.total_seconds()

        return telemetry

    @staticmethod
    def _build_single_lap_telemetry(session, lap, add_distance: bool) -> pd.DataFrame:
        """
        Build one normalized telemetry table for one lap by merging car data and
        position data on nearest timestamp.
        """
        try:
            car = lap.get_car_data().copy()
            pos = lap.get_pos_data().copy()
        except Exception:
            return pd.DataFrame()

        if car.empty:
            return pd.DataFrame()

        if add_distance and hasattr(car, "add_distance") and "Distance" not in car.columns:
            try:
                car = car.add_distance()
            except Exception:
                pass

        car = car.sort_values("Time").reset_index(drop=True)
        pos = pos.sort_values("Time").reset_index(drop=True)

        pos_cols = [c for c in ["Time", "X", "Y", "Z", "Status"] if c in pos.columns]
        if pos_cols == ["Time"]:
            merged = car.copy()
        elif pos_cols:
            merged = pd.merge_asof(
                car,
                pos[pos_cols],
                on="Time",
                direction="nearest"
            )
        else:
            merged = car.copy()

        # Add metadata columns for filtering in dashboard/backend
        merged["Driver"] = lap["Driver"] if "Driver" in lap.index else None
        merged["Team"] = lap["Team"] if "Team" in lap.index else None
        merged["LapNumber"] = int(lap["LapNumber"]) if "LapNumber" in lap.index and pd.notna(lap["LapNumber"]) else None
        merged["LapTime"] = lap["LapTime"] if "LapTime" in lap.index else None
        merged["LapTimeSeconds"] = (
            lap["LapTime"].total_seconds()
            if "LapTime" in lap.index and pd.notna(lap["LapTime"])
            else None
        )
        merged["EventName"] = session.event["EventName"]
        merged["SessionName"] = session.name

        return merged


# -----------------------------
# Simple facade function
# -----------------------------

def load_f1_data(
    year: int,
    event: str | int,
    session_code: str,
    *,
    cache_dir: str | Path = "cache",
    drivers: Optional[list[str]] = None,
    fastest_lap_only: bool = False,
    include_weather: bool = True,
    include_messages: bool = False,
    add_distance: bool = True
) -> TelemetryBundle:
    """
    One-call convenience API for notebooks/apps.
    """
    source = FastF1Source(cache_dir=cache_dir)
    request = SessionRequest(
        year=year,
        event=event,
        session_code=session_code,
        drivers=drivers,
        fastest_lap_only=fastest_lap_only,
        include_weather=include_weather,
        include_messages=include_messages,
        add_distance=add_distance
    )
    return source.load_bundle(request)


def get_events_with_available_laps(
    year: int,
    session_code: str,
    *,
    cache_dir: str | Path = "cache"
) -> list[str]:
    """
    Return event names for which FastF1 can load non-empty lap data.

    This is useful for UI dropdowns so users can select sessions that are
    likely to have telemetry instead of guessing event names manually.
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_path))

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception:
        return []

    if "EventName" not in schedule.columns:
        return []

    available_events: list[str] = []

    for event_name in schedule["EventName"].dropna().astype(str).tolist():
        try:
            session = fastf1.get_session(year, event_name, session_code)
            session.load(laps=True, telemetry=False, weather=False, messages=False)
            laps = session.laps
            if laps is not None and not laps.empty:
                available_events.append(event_name)
        except Exception:
            continue

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(available_events))


def get_schedule_events(year: int) -> list[str]:
    """
    Return event names from the official FastF1 event schedule.
    """
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception:
        return []

    if "EventName" not in schedule.columns:
        return []

    events = schedule["EventName"].dropna().astype(str).tolist()
    return list(dict.fromkeys(events))


if __name__ == "__main__":
    bundle = load_f1_data(
        year=2024,
        event="Monza",
        session_code="Q",
        drivers=["VER", "LEC"],
        fastest_lap_only=True,
        cache_dir="cache"
    )

    print("Session:", bundle.session_info.get("Meeting", {}))
    print("Results shape:", bundle.results.shape)
    print("Laps shape:", bundle.laps.shape)
    print("Telemetry shape:", bundle.telemetry.shape)

    bundle.save("data/processed/2024_monza_q")