from __future__ import annotations

from io import StringIO
from typing import Optional

import pandas as pd

from src.data_loading import TelemetryBundle
from src.database.base_repository import BaseRepository


class SessionRepository(BaseRepository):
    """
    Stores normalized F1 session data locally.

    The local database is the app's persistent read path. FastF1 is only needed
    when a requested session or driver telemetry is not stored yet.
    """

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    year           INTEGER NOT NULL,
                    event          TEXT    NOT NULL,
                    session_code   TEXT    NOT NULL,
                    session_info   TEXT    DEFAULT '{}',
                    results_json   TEXT    DEFAULT '',
                    laps_json      TEXT    DEFAULT '',
                    telemetry_json TEXT    DEFAULT '',
                    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year, event, session_code)
                )
                """
            )

    @staticmethod
    def _df_to_json(df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return ""
        serializable = df.copy()
        for col in serializable.columns:
            if pd.api.types.is_timedelta64_dtype(serializable[col]):
                serializable[col] = serializable[col].dt.total_seconds()
        return serializable.to_json(orient="split", date_format="iso", default_handler=str)

    @staticmethod
    def _json_to_df(value: str | None) -> pd.DataFrame:
        if not value:
            return pd.DataFrame()
        return pd.read_json(StringIO(value), orient="split")

    @staticmethod
    def _merge_telemetry(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
        if existing.empty:
            return incoming.copy()
        if incoming.empty:
            return existing.copy()
        merged = pd.concat([existing, incoming], ignore_index=True)
        keys = [c for c in ["Driver", "LapNumber", "Time", "Distance"] if c in merged.columns]
        if keys:
            merged = merged.drop_duplicates(subset=keys, keep="last")
        return merged

    def load_session(self, year: int, event: str, session_code: str) -> Optional[TelemetryBundle]:
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT session_info, results_json, laps_json, telemetry_json
                FROM sessions
                WHERE year = ? AND event = ? AND session_code = ?
                """,
                (int(year), str(event), str(session_code)),
            ).fetchone()
        if row is None:
            return None

        return TelemetryBundle(
            session_info={},
            results=self._json_to_df(row["results_json"]),
            laps=self._json_to_df(row["laps_json"]),
            weather=pd.DataFrame(),
            telemetry=self._json_to_df(row["telemetry_json"]),
            track_status=pd.DataFrame(),
            session_status=pd.DataFrame(),
            race_control_messages=pd.DataFrame(),
        )

    def save_session(
        self,
        year: int,
        event: str,
        session_code: str,
        bundle: TelemetryBundle,
    ) -> None:
        self.ensure_schema()
        existing = self.load_session(year, event, session_code)
        telemetry = bundle.telemetry
        if existing is not None:
            telemetry = self._merge_telemetry(existing.telemetry, bundle.telemetry)
            if bundle.results.empty:
                bundle.results = existing.results
            if bundle.laps.empty:
                bundle.laps = existing.laps

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (year, event, session_code, results_json, laps_json, telemetry_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(year, event, session_code) DO UPDATE SET
                    results_json   = excluded.results_json,
                    laps_json      = excluded.laps_json,
                    telemetry_json = excluded.telemetry_json,
                    updated_at     = excluded.updated_at
                """,
                (
                    int(year),
                    str(event),
                    str(session_code),
                    self._df_to_json(bundle.results),
                    self._df_to_json(bundle.laps),
                    self._df_to_json(telemetry),
                ),
            )
