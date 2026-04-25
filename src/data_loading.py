from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterable

import pandas as pd
import fastf1


@dataclass(frozen=True)
class SessionRequest:
    """
    Immutable value object describing a single F1 session to load.

    Pattern: Value Object (DDD)
    """

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
    """
    Aggregates all normalized DataFrames produced from one F1 session load.

    Pattern: Data Transfer Object (DTO)
    Principle: SRP – pure data container, no business logic except persistence
    """

    session_info: dict
    results: pd.DataFrame
    laps: pd.DataFrame
    weather: pd.DataFrame
    telemetry: pd.DataFrame
    track_status: pd.DataFrame
    session_status: pd.DataFrame
    race_control_messages: pd.DataFrame

    def save(self, output_dir: str | Path) -> None:
        """Persists all normalized tables to parquet files."""
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


class TelemetrySource(ABC):
    @abstractmethod
    def load_bundle(self, request: SessionRequest) -> TelemetryBundle:
        raise NotImplementedError


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

    @staticmethod
    def build_driver_map(results_df: pd.DataFrame) -> dict[str, str]:
        """Map DriverNumber → Driver abbreviation from a results DataFrame."""
        if results_df.empty or not {"DriverNumber", "Driver"}.issubset(results_df.columns):
            return {}
        return dict(zip(
            results_df["DriverNumber"].astype(str),
            results_df["Driver"].astype(str),
        ))

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

        results_df = self._normalize_results(session)

        driver_map = self.build_driver_map(results_df)

        laps_df = self._normalize_laps(session, driver_map=driver_map)
        telemetry_df = self._build_telemetry_dataframe(
            session=session,
            laps_df=laps_df,
            drivers=request.drivers,
            fastest_lap_only=request.fastest_lap_only,
            add_distance=request.add_distance,
            driver_map=driver_map
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
    def _normalize_results(session) -> pd.DataFrame:
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

        if "DriverNumber" in results.columns:
            results["DriverNumber"] = results["DriverNumber"].astype(str)
        if "Driver" in results.columns:
            results["Driver"] = results["Driver"].astype(str)

        results["EventName"] = session.event["EventName"]
        results["Year"] = session.event["EventDate"].year if "EventDate" in session.event else None
        results["SessionName"] = session.name
        return results

    @staticmethod
    def _normalize_laps(session, driver_map: dict[str, str] | None = None) -> pd.DataFrame:
        try:
            laps = session.laps.copy()
        except Exception:
            return pd.DataFrame()
        
        if driver_map and "Driver" in laps.columns:
            laps["Driver"] = laps["Driver"].astype(str).map(driver_map).fillna(laps["Driver"].astype(str))

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

    def _build_telemetry_dataframe(
    self,
    session,
    laps_df: pd.DataFrame,
    drivers: Optional[Iterable[str]],
    fastest_lap_only: bool,
    add_distance: bool,
    driver_map: dict[str, str] | None = None,
) -> pd.DataFrame:
        if laps_df.empty:
            return pd.DataFrame()

        try:
            session_laps = session.laps.copy()
        except Exception:
            return pd.DataFrame()

        if driver_map and "Driver" in session_laps.columns:
            session_laps["Driver"] = (
                session_laps["Driver"]
                .astype(str)
                .map(driver_map)
                .fillna(session_laps["Driver"].astype(str))
            )

        available_drivers = sorted(laps_df["Driver"].dropna().astype(str).unique().tolist())
        selected_drivers = [str(d) for d in drivers] if drivers else available_drivers

        telemetry_frames: list[pd.DataFrame] = []

        for driver in selected_drivers:
            driver_laps = session_laps[session_laps["Driver"] == driver]
            if driver_laps.empty:
                continue

            if fastest_lap_only:
                fastest = driver_laps.pick_fastest()
                lap_candidates = [fastest] if fastest is not None else []
            else:
                lap_candidates = [lap for _, lap in driver_laps.iterlaps()]

            for lap in lap_candidates:
                lap_frame = self._merge_single_lap_telemetry(
                    session=session,
                    lap=lap,
                    add_distance=add_distance,
                    driver_map=driver_map,
                )
                if not lap_frame.empty:
                    telemetry_frames.append(lap_frame)

        if not telemetry_frames:
            return pd.DataFrame()

        telemetry = pd.concat(telemetry_frames, ignore_index=True)

        if "Time" in telemetry.columns:
            telemetry["TimeSeconds"] = telemetry["Time"].dt.total_seconds()

        if "SessionTime" in telemetry.columns:
            telemetry["SessionTimeSeconds"] = telemetry["SessionTime"].dt.total_seconds()

        return telemetry

    @staticmethod
    def _merge_single_lap_telemetry(
        session,
        lap,
        add_distance: bool,
        driver_map: dict[str, str] | None = None,
    ) -> pd.DataFrame:
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

        raw_driver = str(lap["Driver"]) if "Driver" in lap.index and pd.notna(lap["Driver"]) else None
        normalized_driver = driver_map.get(raw_driver, raw_driver) if driver_map and raw_driver is not None else raw_driver

        merged["Driver"] = normalized_driver
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




class F1SessionBundleCache:
    """
    Caches FastF1 session objects and provides high-level loading methods.

    Responsibilities:
    - cache session objects to avoid redundant session.load() calls
    - quick-load (laps only, no telemetry) for dashboard overview
    - on-demand telemetry extraction per driver
    - preload into FastF1 disk cache
    """

    def __init__(self, cache_dir: str | Path = "cache") -> None:
        self._cache_dir = Path(cache_dir)
        self._cache: dict[str, tuple] = {}

    def _make_cache_key(self, year: int, event: str | int, session_code: str) -> str:
        return f"{year}|{event}|{session_code}"

    def load_quick(
        self,
        year: int,
        event: str | int,
        session_code: str,
    ) -> TelemetryBundle:
        """
        Fast session load: results + laps only, no telemetry processing.
        Caches the session object for later per-driver telemetry extraction.
        """
        source = FastF1Source(cache_dir=self._cache_dir)
        session = fastf1.get_session(year, event, session_code)
        session.load(laps=True, telemetry=False, weather=False, messages=False)

        self._cache[self._make_cache_key(year, event, session_code)] = (session, source)

        results_df = source._normalize_results(session)
        driver_map = source.build_driver_map(results_df)
        laps_df = source._normalize_laps(session, driver_map=driver_map)

        return TelemetryBundle(
            session_info=dict(session.session_info),
            results=results_df.reset_index(drop=True),
            laps=laps_df.reset_index(drop=True),
            weather=pd.DataFrame(),
            telemetry=pd.DataFrame(),
            track_status=pd.DataFrame(),
            session_status=pd.DataFrame(),
            race_control_messages=pd.DataFrame(),
        )

    def load_driver_telemetry(
        self,
        year: int,
        event: str | int,
        session_code: str,
        driver: str,
    ) -> pd.DataFrame:
        """
        Extract telemetry for a single driver.
        Reuses cached session objects; loads telemetry additively if needed.
        """
        key = self._make_cache_key(year, event, session_code)
        cached = self._cache.get(key)

        if cached:
            session, source = cached
        else:
            source = FastF1Source(cache_dir=self._cache_dir)
            session = fastf1.get_session(year, event, session_code)
            self._cache[key] = (session, source)

        # Additive — no-op if telemetry already loaded
        session.load(laps=True, telemetry=True, weather=False, messages=False)

        results_df = source._normalize_results(session)
        driver_map = source.build_driver_map(results_df)
        laps_df = source._normalize_laps(session, driver_map=driver_map)

        return source._build_telemetry_dataframe(
            session=session,
            laps_df=laps_df,
            drivers=[driver],
            fastest_lap_only=False,
            add_distance=True,
            driver_map=driver_map,
        )

    def load_full(
        self,
        year: int,
        event: str | int,
        session_code: str,
        drivers: Optional[list[str]] = None,
        fastest_lap_only: bool = False,
        include_weather: bool = True,
        include_messages: bool = False,
        add_distance: bool = True,
    ) -> TelemetryBundle:
        """Full load including telemetry — used by notebooks/Streamlit app."""
        source = FastF1Source(cache_dir=self._cache_dir)
        request = SessionRequest(
            year=year,
            event=event,
            session_code=session_code,
            drivers=drivers,
            fastest_lap_only=fastest_lap_only,
            include_weather=include_weather,
            include_messages=include_messages,
            add_distance=add_distance,
        )
        return source.load_bundle(request)

    @staticmethod
    def preload(year: int, event: str, session_code: str, cache_dir: str | Path = "cache"):
        """Download laps + telemetry into FastF1 disk cache (no merging)."""
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(cache_path))

        session = fastf1.get_session(year, event, session_code)
        session.load(laps=True, telemetry=True, weather=False, messages=False)



class F1ScheduleService:
    """
    Provides event schedule lookups from FastF1.

    Pattern: Monostate – every instance shares the same event cache dict,
    so results fetched by one caller are immediately visible to all others
    without requiring a global Singleton reference.
    """

    _shared_state: dict = {"_event_cache": {}, "_cache_dir": "cache"}

    def __init__(self) -> None:
        self.__dict__ = F1ScheduleService._shared_state

    def get_events(self, year: int) -> list[str]:
        """Return event names from the official schedule (cached)."""
        if year in self._event_cache:
            return self._event_cache[year]

        fastf1.Cache.enable_cache(self._cache_dir)
        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
        except Exception:
            return []

        if "EventName" not in schedule.columns:
            return []

        events = list(dict.fromkeys(schedule["EventName"].dropna().astype(str).tolist()))
        self._event_cache[year] = events
        return events

    def get_events_with_laps(
        self,
        year: int,
        session_code: str,
        *,
        cache_dir: str | Path = "cache",
    ) -> list[str]:
        """Return events that have non-empty lap data available."""
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(cache_path))

        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
        except Exception:
            return []

        if "EventName" not in schedule.columns:
            return []

        available: list[str] = []
        for event_name in schedule["EventName"].dropna().astype(str).tolist():
            try:
                session = fastf1.get_session(year, event_name, session_code)
                session.load(laps=True, telemetry=False, weather=False, messages=False)
                if session.laps is not None and not session.laps.empty:
                    available.append(event_name)
            except Exception:
                continue

        return list(dict.fromkeys(available))



_default_session_cache = F1SessionBundleCache()




def load_session_quick(
    year: int,
    event: str | int,
    session_code: str,
    *,
    cache_dir: str | Path = "cache",
) -> TelemetryBundle:
    return _default_session_cache.load_quick(year, event, session_code)


def load_driver_telemetry(
    year: int,
    event: str | int,
    session_code: str,
    driver: str,
    *,
    cache_dir: str | Path = "cache",
) -> pd.DataFrame:
    return _default_session_cache.load_driver_telemetry(year, event, session_code, driver)


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
    add_distance: bool = True,
) -> TelemetryBundle:
    return _default_session_cache.load_full(
        year, event, session_code,
        drivers=drivers,
        fastest_lap_only=fastest_lap_only,
        include_weather=include_weather,
        include_messages=include_messages,
        add_distance=add_distance,
    )


def cache_session(year: int, event: str, session_code: str, cache_dir: str | Path = "cache"):
    F1SessionBundleCache.preload(year, event, session_code, cache_dir)


def get_schedule_events(year: int) -> list[str]:
    return F1ScheduleService().get_events(year)


def get_events_with_available_laps(
    year: int,
    session_code: str,
    *,
    cache_dir: str | Path = "cache",
) -> list[str]:
    return F1ScheduleService().get_events_with_laps(year, session_code, cache_dir=cache_dir)
