from __future__ import annotations

import pandas as pd


def get_available_drivers(telemetry_df: pd.DataFrame) -> list[str]:
    if telemetry_df.empty or "Driver" not in telemetry_df.columns:
        return []
    return sorted(telemetry_df["Driver"].dropna().unique().tolist())


def get_driver_laps(telemetry_df: pd.DataFrame, driver: str) -> list[int]:
    df = telemetry_df[telemetry_df["Driver"] == driver].copy()
    if df.empty or "LapNumber" not in df.columns:
        return []
    laps = df["LapNumber"].dropna().astype(int).unique().tolist()
    return sorted(laps)


def get_driver_telemetry(telemetry_df: pd.DataFrame, driver: str) -> pd.DataFrame:
    return telemetry_df[telemetry_df["Driver"] == driver].copy()


def get_lap_telemetry(
    telemetry_df: pd.DataFrame,
    driver: str,
    lap_number: int
) -> pd.DataFrame:
    df = telemetry_df[
        (telemetry_df["Driver"] == driver) &
        (telemetry_df["LapNumber"] == lap_number)
    ].copy()

    return df.sort_values("Distance") if "Distance" in df.columns else df


def get_multiple_laps_telemetry(
    telemetry_df: pd.DataFrame,
    driver: str,
    lap_numbers: list[int]
) -> pd.DataFrame:
    df = telemetry_df[
        (telemetry_df["Driver"] == driver) &
        (telemetry_df["LapNumber"].isin(lap_numbers))
    ].copy()

    return df.sort_values(["LapNumber", "Distance"]) if "Distance" in df.columns else df


def get_fastest_laps_for_driver(
    telemetry_df: pd.DataFrame,
    driver: str,
    top_n: int = 3
) -> list[int]:
    df = telemetry_df[telemetry_df["Driver"] == driver].copy()
    if df.empty or "LapTimeSeconds" not in df.columns or "LapNumber" not in df.columns:
        return []

    lap_times = (
        df[["LapNumber", "LapTimeSeconds"]]
        .dropna()
        .drop_duplicates()
        .sort_values("LapTimeSeconds")
    )

    return lap_times.head(top_n)["LapNumber"].astype(int).tolist()


def get_lap_summary(
    telemetry_df: pd.DataFrame,
    driver: str,
    lap_numbers: list[int]
) -> pd.DataFrame:
    df = get_multiple_laps_telemetry(telemetry_df, driver, lap_numbers)
    if df.empty:
        return pd.DataFrame()

    summary = (
        df.groupby("LapNumber", as_index=False)
        .agg(
            LapTimeSeconds=("LapTimeSeconds", "first"),
            MaxSpeed=("Speed", "max"),
            MeanSpeed=("Speed", "mean"),
            MeanThrottle=("Throttle", "mean"),
            BrakeEvents=("Brake", lambda s: int((s > 0).sum()) if s.notna().any() else 0),
        )
        .sort_values("LapNumber")
    )
    return summary

def get_results_table(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return pd.DataFrame()

    cols = [c for c in [
        "FinishPosition",
        "Driver",
        "Team",
        "GridPosition",
        "Points",
        "Q1",
        "Q2",
        "Q3",
        "Time",
        "Status"
    ] if c in results_df.columns]

    out = results_df[cols].copy()

    if "FinishPosition" in out.columns:
        out = out.sort_values("FinishPosition")

    return out