from __future__ import annotations

import pandas as pd


def get_available_drivers(telemetry_df: pd.DataFrame) -> list[str]:
    if telemetry_df.empty or "Driver" not in telemetry_df.columns:
        return []
    return sorted(telemetry_df["Driver"].dropna().astype(str).unique().tolist())


def get_driver_laps(telemetry_df: pd.DataFrame, driver: str) -> list[int]:
    if telemetry_df.empty or "Driver" not in telemetry_df.columns or "LapNumber" not in telemetry_df.columns:
        return []

    df = telemetry_df[telemetry_df["Driver"].astype(str) == str(driver)].copy()
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


def get_driver_telemetry(telemetry_df: pd.DataFrame, driver: str) -> pd.DataFrame:
    if telemetry_df.empty or "Driver" not in telemetry_df.columns:
        return pd.DataFrame()
    return telemetry_df[telemetry_df["Driver"].astype(str) == str(driver)].copy()


def get_lap_telemetry(
    telemetry_df: pd.DataFrame,
    driver: str,
    lap_number: int
) -> pd.DataFrame:
    if telemetry_df.empty:
        return pd.DataFrame()
    if "Driver" not in telemetry_df.columns or "LapNumber" not in telemetry_df.columns:
        return pd.DataFrame()

    df = telemetry_df[
        (telemetry_df["Driver"].astype(str) == str(driver)) &
        (pd.to_numeric(telemetry_df["LapNumber"], errors="coerce") == int(lap_number))
    ].copy()

    return df.sort_values("Distance") if "Distance" in df.columns else df


def get_multiple_laps_telemetry(
    telemetry_df: pd.DataFrame,
    driver: str,
    lap_numbers: list[int]
) -> pd.DataFrame:
    if telemetry_df.empty or not lap_numbers:
        return pd.DataFrame()
    if "Driver" not in telemetry_df.columns or "LapNumber" not in telemetry_df.columns:
        return pd.DataFrame()

    lap_numbers = [int(x) for x in lap_numbers]

    df = telemetry_df.copy()
    df["Driver"] = df["Driver"].astype(str)
    df["LapNumber"] = pd.to_numeric(df["LapNumber"], errors="coerce")

    df = df[
        (df["Driver"] == str(driver)) &
        (df["LapNumber"].isin(lap_numbers))
    ].copy()

    df = df[df["LapNumber"].notna()].copy()
    df["LapNumber"] = df["LapNumber"].astype(int)

    return df.sort_values(["LapNumber", "Distance"]) if "Distance" in df.columns else df


def get_fastest_laps_for_driver(
    telemetry_df: pd.DataFrame,
    driver: str,
    top_n: int = 3
) -> list[int]:
    if telemetry_df.empty:
        return []
    if "Driver" not in telemetry_df.columns or "LapTimeSeconds" not in telemetry_df.columns or "LapNumber" not in telemetry_df.columns:
        return []

    df = telemetry_df[telemetry_df["Driver"].astype(str) == str(driver)].copy()
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

    summary["LapNumber"] = pd.to_numeric(summary["LapNumber"], errors="coerce").astype("Int64")
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

    timedelta_cols = [c for c in ["Q1", "Q2", "Q3", "Time"] if c in out.columns]
    for col in timedelta_cols:
        out[col] = out[col].astype(str)

    if "Driver" in out.columns:
        out["Driver"] = out["Driver"].astype(str)

    if "FinishPosition" in out.columns:
        out = out.sort_values("FinishPosition")

    return out