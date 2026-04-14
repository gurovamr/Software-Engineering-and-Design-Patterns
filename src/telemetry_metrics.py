import pandas as pd


class TelemetryService:
    """
    Encapsulates all telemetry analysis operations on a session DataFrame.

    Responsibilities:
    - Filter telemetry by driver / lap
    - Summarise lap performance (speed, throttle, brake, lap time)
    - Identify fastest laps
    - Build results tables for display

    Pattern: Service
    """

    def __init__(self, telemetry_df: pd.DataFrame) -> None:
        self._df = telemetry_df

    # ── Driver / Lap filters ────────────────────────────────────────────────

    def get_available_drivers(self) -> list[str]:
        if self._df.empty or "Driver" not in self._df.columns:
            return []
        return sorted(self._df["Driver"].dropna().astype(str).unique().tolist())

    def get_driver_laps(self, driver: str) -> list[int]:
        if self._df.empty or "Driver" not in self._df.columns or "LapNumber" not in self._df.columns:
            return []
        df = self._df[self._df["Driver"].astype(str) == str(driver)].copy()
        if df.empty:
            return []
        laps = (
            pd.to_numeric(df["LapNumber"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )
        return sorted(int(x) for x in laps)

    def get_driver_telemetry(self, driver: str) -> pd.DataFrame:
        if self._df.empty or "Driver" not in self._df.columns:
            return pd.DataFrame()
        return self._df[self._df["Driver"].astype(str) == str(driver)].copy()

    def get_lap_telemetry(self, driver: str, lap_number: int) -> pd.DataFrame:
        if self._df.empty or "Driver" not in self._df.columns or "LapNumber" not in self._df.columns:
            return pd.DataFrame()
        df = self._df[
            (self._df["Driver"].astype(str) == str(driver)) &
            (pd.to_numeric(self._df["LapNumber"], errors="coerce") == int(lap_number))
        ].copy()
        return df.sort_values("Distance") if "Distance" in df.columns else df

    def get_multiple_laps_telemetry(self, driver: str, lap_numbers: list[int]) -> pd.DataFrame:
        if self._df.empty or not lap_numbers:
            return pd.DataFrame()
        if "Driver" not in self._df.columns or "LapNumber" not in self._df.columns:
            return pd.DataFrame()
        lap_numbers = [int(x) for x in lap_numbers]
        df = self._df.copy()
        df["Driver"] = df["Driver"].astype(str)
        df["LapNumber"] = pd.to_numeric(df["LapNumber"], errors="coerce")
        df = df[(df["Driver"] == str(driver)) & (df["LapNumber"].isin(lap_numbers))].copy()
        df = df[df["LapNumber"].notna()].copy()
        df["LapNumber"] = df["LapNumber"].astype(int)
        return df.sort_values(["LapNumber", "Distance"]) if "Distance" in df.columns else df

    # ── Performance analysis ────────────────────────────────────────────────

    def get_fastest_laps_for_driver(self, driver: str, top_n: int = 3) -> list[int]:
        if self._df.empty:
            return []
        required = {"Driver", "LapTimeSeconds", "LapNumber"}
        if not required.issubset(self._df.columns):
            return []
        df = self._df[self._df["Driver"].astype(str) == str(driver)].copy()
        if df.empty:
            return []
        df["LapNumber"] = pd.to_numeric(df["LapNumber"], errors="coerce")
        df["LapTimeSeconds"] = pd.to_numeric(df["LapTimeSeconds"], errors="coerce")
        lap_times = (
            df[["LapNumber", "LapTimeSeconds"]]
            .dropna()
            .drop_duplicates()
            .sort_values("LapTimeSeconds")
        )
        return lap_times.head(top_n)["LapNumber"].astype(int).tolist()

    def get_lap_summary(self, driver: str, lap_numbers: list[int]) -> pd.DataFrame:
        df = self.get_multiple_laps_telemetry(driver, lap_numbers)
        if df.empty:
            return pd.DataFrame()
        return (
            df.groupby("LapNumber", as_index=False)
            .agg(
                LapTimeSeconds=("LapTimeSeconds", "first"),
                MaxSpeed=("Speed", "max"),
                MeanSpeed=("Speed", "mean"),
                MeanThrottle=("Throttle", "mean"),
                BrakeEvents=("Brake", lambda s: int((s > 0).sum()) if s.notna().any() else 0),
            )
            .sort_values("LapNumber")
            .assign(LapNumber=lambda d: pd.to_numeric(d["LapNumber"], errors="coerce").astype("Int64"))
        )

    # ── Results table ───────────────────────────────────────────────────────

    @staticmethod
    def build_results_table(results_df: pd.DataFrame) -> pd.DataFrame:
        """Selects and formats the columns relevant for the UI results table."""
        if results_df.empty:
            return pd.DataFrame()
        cols = [c for c in [
            "FinishPosition", "Driver", "Team", "GridPosition",
            "Points", "Q1", "Q2", "Q3", "Time", "Status",
        ] if c in results_df.columns]
        out = results_df[cols].copy()
        for col in [c for c in ["Q1", "Q2", "Q3", "Time"] if c in out.columns]:
            out[col] = out[col].astype(str)
        if "Driver" in out.columns:
            out["Driver"] = out["Driver"].astype(str)
        if "FinishPosition" in out.columns:
            out = out.sort_values("FinishPosition")
        return out


# ── Backward-compatible module-level wrappers ──────────────────────────────
# Delegate to TelemetryService so existing call sites require no changes.

def get_available_drivers(telemetry_df: pd.DataFrame) -> list[str]:
    return TelemetryService(telemetry_df).get_available_drivers()


def get_driver_laps(telemetry_df: pd.DataFrame, driver: str) -> list[int]:
    return TelemetryService(telemetry_df).get_driver_laps(driver)


def get_driver_telemetry(telemetry_df: pd.DataFrame, driver: str) -> pd.DataFrame:
    return TelemetryService(telemetry_df).get_driver_telemetry(driver)


def get_lap_telemetry(telemetry_df: pd.DataFrame, driver: str, lap_number: int) -> pd.DataFrame:
    return TelemetryService(telemetry_df).get_lap_telemetry(driver, lap_number)


def get_multiple_laps_telemetry(
    telemetry_df: pd.DataFrame, driver: str, lap_numbers: list[int]
) -> pd.DataFrame:
    return TelemetryService(telemetry_df).get_multiple_laps_telemetry(driver, lap_numbers)


def get_fastest_laps_for_driver(
    telemetry_df: pd.DataFrame, driver: str, top_n: int = 3
) -> list[int]:
    return TelemetryService(telemetry_df).get_fastest_laps_for_driver(driver, top_n)


def get_lap_summary(
    telemetry_df: pd.DataFrame, driver: str, lap_numbers: list[int]
) -> pd.DataFrame:
    return TelemetryService(telemetry_df).get_lap_summary(driver, lap_numbers)


def get_results_table(results_df: pd.DataFrame) -> pd.DataFrame:
    return TelemetryService.build_results_table(results_df)


def extract_pit_stops(laps_df: pd.DataFrame) -> list[dict]:
    return PitStopExtractor.extract(laps_df)


class PitStopExtractor:
    """
    Extracts pit stop events from a laps DataFrame.

    Responsibilities:
    - Identify laps where a pit stop occurred
    - Return structured event records for UI display

    Pattern: Service (stateless utility)
    """

    @staticmethod
    def extract(laps_df: pd.DataFrame) -> list[dict]:
        """Returns a list of pit stop events sorted by lap and driver."""
        events: list[dict] = []
        if laps_df.empty:
            return events
        if "PitInTime" in laps_df.columns:
            pits = laps_df[laps_df["PitInTime"].notna()].copy()
            for _, row in pits.iterrows():
                driver = str(row.get("Driver", "?"))
                lap = int(row["LapNumber"]) if pd.notna(row.get("LapNumber")) else 0
                events.append({"driver": driver, "lap": lap, "type": "PIT"})
        return sorted(events, key=lambda e: (e["lap"], e["driver"]))