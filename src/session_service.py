from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data_loading import TelemetryBundle, load_driver_telemetry, load_session_quick
from src.database.session_repository import SessionRepository


@dataclass(frozen=True)
class SessionLoadResult:
    bundle: TelemetryBundle
    source: str
    message: str


@dataclass(frozen=True)
class DriverTelemetryResult:
    bundle: TelemetryBundle
    telemetry: pd.DataFrame
    source: str
    message: str


@dataclass(frozen=True)
class EventCacheResult:
    loaded: list[str]
    already_local: list[str]
    unavailable: list[str]
    stopped_by_rate_limit: bool

    @property
    def total_available(self) -> int:
        return len(self.loaded) + len(self.already_local)


class SessionService:
    """DB-first facade for session overview and telemetry loading."""

    EVENT_SESSION_CODES = ["FP1", "FP2", "FP3", "Q", "SQ", "S", "R"]

    def __init__(self, db_path: str | Path, cache_dir: str | Path = "cache") -> None:
        self._repo = SessionRepository(db_path)
        self._cache_dir = cache_dir

    def load_session_overview(
        self,
        year: int,
        event: str,
        session_code: str,
    ) -> SessionLoadResult:
        stored = self._repo.load_session(year, event, session_code)
        if stored is not None and not stored.laps.empty:
            return SessionLoadResult(
                bundle=stored,
                source="local",
                message="Loaded session from local database.",
            )

        try:
            bundle = load_session_quick(
                year=year,
                event=event,
                session_code=session_code,
                cache_dir=self._cache_dir,
            )
        except Exception:
            if stored is not None and not stored.results.empty:
                return SessionLoadResult(
                    bundle=stored,
                    source="partial",
                    message="Loaded partial local data. Lap data is missing and FastF1 could not be reached.",
                )
            raise
        self._repo.save_session(year, event, session_code, bundle)
        if bundle.laps.empty:
            message = "Fetched session, but no lap data was available. Results may still be shown."
        else:
            message = "Fetched session from FastF1 and stored it locally."
        return SessionLoadResult(
            bundle=bundle,
            source="fastf1",
            message=message,
        )

    def load_driver_telemetry(
        self,
        year: int,
        event: str,
        session_code: str,
        driver: str,
    ) -> DriverTelemetryResult:
        stored = self._repo.load_session(year, event, session_code)
        if stored is None:
            overview = self.load_session_overview(year, event, session_code)
            stored = overview.bundle

        telemetry = self._driver_slice(stored.telemetry, driver)
        if not telemetry.empty:
            return DriverTelemetryResult(
                bundle=stored,
                telemetry=telemetry,
                source="local",
                message=f"Loaded {driver} telemetry from local database.",
            )

        telemetry = load_driver_telemetry(
            year,
            event,
            session_code,
            driver,
            cache_dir=self._cache_dir,
        )
        if telemetry.empty:
            return DriverTelemetryResult(
                bundle=stored,
                telemetry=telemetry,
                source="empty",
                message=f"No telemetry was available for {driver}.",
            )

        updated = TelemetryBundle(
            session_info=stored.session_info,
            results=stored.results,
            laps=stored.laps,
            weather=stored.weather,
            telemetry=telemetry,
            track_status=stored.track_status,
            session_status=stored.session_status,
            race_control_messages=stored.race_control_messages,
        )
        self._repo.save_session(year, event, session_code, updated)
        refreshed = self._repo.load_session(year, event, session_code) or updated
        return DriverTelemetryResult(
            bundle=refreshed,
            telemetry=self._driver_slice(refreshed.telemetry, driver),
            source="fastf1",
            message=f"Fetched {driver} telemetry from FastF1 and stored it locally.",
        )

    def cache_full_event(self, year: int, event: str) -> EventCacheResult:
        """
        Cache all available session overviews for one Grand Prix weekend.

        This intentionally stores results/laps only. Driver telemetry is still
        fetched on demand because full telemetry for every driver/session is much
        heavier and more likely to hit FastF1 limits.
        """
        loaded: list[str] = []
        already_local: list[str] = []
        unavailable: list[str] = []
        stopped_by_rate_limit = False

        for session_code in self.EVENT_SESSION_CODES:
            try:
                result = self.load_session_overview(year, event, session_code)
            except Exception as exc:
                if self._is_rate_limit_error(exc):
                    stopped_by_rate_limit = True
                    break
                unavailable.append(session_code)
                continue

            if result.source == "local":
                already_local.append(session_code)
            elif result.bundle.laps.empty:
                unavailable.append(session_code)
            else:
                loaded.append(session_code)

        return EventCacheResult(
            loaded=loaded,
            already_local=already_local,
            unavailable=unavailable,
            stopped_by_rate_limit=stopped_by_rate_limit,
        )

    @staticmethod
    def _driver_slice(telemetry: pd.DataFrame, driver: str) -> pd.DataFrame:
        if telemetry.empty or "Driver" not in telemetry.columns:
            return pd.DataFrame()
        return telemetry[telemetry["Driver"].astype(str) == str(driver)].copy()

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        return exc.__class__.__name__ == "RateLimitExceededError"
