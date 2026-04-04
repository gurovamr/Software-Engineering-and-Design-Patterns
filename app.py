from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data_loading import (
    load_f1_data,
    get_events_with_available_laps,
    get_schedule_events,
)
from src.telemetry_metrics import (
    get_available_drivers,
    get_driver_laps,
    get_multiple_laps_telemetry,
    get_lap_summary,
    get_fastest_laps_for_driver,
    get_results_table,
)
from src.visualization import (
    SpeedChart,
    ThrottleBrakeChart,
    GearChart,
    TrackMapChart,
    LapSummaryChart,
)



@dataclass(frozen=True)
class SessionSelection:
    """Immutable record of the user's session choice."""
    year: int
    event: str
    session_code: str
    cache_dir: str


@dataclass(frozen=True)
class DriverSelection:
    """Immutable record of the user's driver / lap choice."""
    driver: str
    laps: list[int]



class DataService:
    """Thin wrapper around data-loading functions with Streamlit caching."""

    SESSION_OPTIONS = ["R", "Q", "FP1", "FP2", "FP3", "S", "SQ"]

    @staticmethod
    @st.cache_data(show_spinner=False)
    def load_bundle(year: int, event: str, session_code: str, cache_dir: str):
        return load_f1_data(
            year=year,
            event=event,
            session_code=session_code,
            cache_dir=cache_dir,
            fastest_lap_only=False,
        )

    @staticmethod
    @st.cache_data(show_spinner=False)
    def available_events(year: int, session_code: str, cache_dir: str):
        return get_events_with_available_laps(
            year=year, session_code=session_code, cache_dir=cache_dir
        )

    @staticmethod
    @st.cache_data(show_spinner=False)
    def schedule_events(year: int):
        return get_schedule_events(year)



class Sidebar:
    """All sidebar UI controls for session and driver selection."""

    @staticmethod
    def select_session() -> SessionSelection:
        with st.sidebar:
            st.header("Session Selection")
            year = st.number_input(
                "Year", min_value=2018, max_value=2026, value=2024, step=1
            )
            session_code = st.selectbox(
                "Session", DataService.SESSION_OPTIONS, index=1
            )
            cache_dir = st.text_input("Cache directory", value="cache")

        with st.spinner("Checking which events have lap data for this year/session..."):
            available = DataService.available_events(year, session_code, cache_dir)
        schedule = DataService.schedule_events(year)

        with st.sidebar:
            event = Sidebar._event_picker(available, schedule)

        return SessionSelection(year, event, session_code, cache_dir)

    @staticmethod
    def select_driver(telemetry: pd.DataFrame, results: pd.DataFrame) -> DriverSelection:
        drivers = get_available_drivers(telemetry)
        if not drivers:
            st.error("No drivers found in telemetry.")
            st.stop()

        default_driver = drivers[0]
        if not results.empty and "Driver" in results.columns:
            top = results["Driver"].dropna().tolist()
            if top and top[0] in drivers:
                default_driver = top[0]

        with st.sidebar:
            st.header("Telemetry Selection")
            driver = st.selectbox(
                "Driver",
                drivers,
                index=drivers.index(default_driver) if default_driver in drivers else 0,
            )
            available_laps = get_driver_laps(telemetry, driver)
            default_laps = get_fastest_laps_for_driver(telemetry, driver, top_n=2)
            if not default_laps and available_laps:
                default_laps = available_laps[:2]

            selected = st.multiselect(
                "Laps to compare", options=available_laps, default=default_laps
            )

        if not selected:
            st.warning("Please select at least one lap.")
            st.stop()

        return DriverSelection(driver, selected)

  
    @staticmethod
    def _event_picker(available: list[str], schedule: list[str]) -> str:
        if available:
            default = "Monza" if "Monza" in available else available[0]
            event = st.selectbox(
                "Race / Event",
                options=available,
                index=available.index(default),
            )
            st.caption(f"{len(available)} events found with lap data.")
        elif schedule:
            default = "Monza" if "Monza" in schedule else schedule[0]
            event = st.selectbox(
                "Race / Event",
                options=schedule,
                index=schedule.index(default),
            )
            st.caption(
                "No events could be verified with lap telemetry right now. "
                "Showing full race schedule."
            )
        else:
            st.warning("No events with lap data were detected. Use manual input.")
            event = st.text_input("Race / Event", value="Monza")
        return event



class Dashboard:
    """Renders the main content area with metrics, tables, and charts."""

    def __init__(
        self,
        session: SessionSelection,
        driver: str,
        lap_df: pd.DataFrame,
        summary_df: pd.DataFrame,
        results: pd.DataFrame,
        selected_laps: list[int],
    ):
        self._session = session
        self._driver = driver
        self._lap_df = lap_df
        self._summary = summary_df
        self._results = results
        self._laps = selected_laps

    def render(self) -> None:
        self._render_header()
        self._render_results()
        self._render_lap_comparison()
        self._render_lap_summary()
        self._render_charts()
        self._render_raw_data()

        c1, c2, c3 = st.columns(3)
        c1.metric("Selected Laps", len(self._laps))
        c2.metric(
            "Max Speed",
            f"{self._lap_df['Speed'].max():.1f} km/h"
            if "Speed" in self._lap_df.columns
            else "n/a",
        )
        c3.metric("Telemetry Samples", len(self._lap_df))

    def _render_results(self) -> None:
        table = get_results_table(self._results)
        st.subheader("Driver Ranking / Classification")
        st.dataframe(table, use_container_width=True, hide_index=True)

    def _render_lap_comparison(self) -> None:
        st.subheader("Lap Comparison")
        if len(self._laps) >= 2 and not self._summary.empty:
            st.plotly_chart(
                LapSummaryChart(self._summary).render(), use_container_width=True
            )
        elif not self._summary.empty:
            best = self._summary.iloc[0]
            st.metric("Lap Time", f"{best['LapTimeSeconds']:.3f} s")

    def _render_lap_summary(self) -> None:
        st.subheader("Lap Summary")
        if not self._summary.empty:
            st.dataframe(self._summary, use_container_width=True, hide_index=True)
        else:
            st.info("No lap summary available.")

    def _render_charts(self) -> None:
        st.subheader("Telemetry Analysis")
        df = self._lap_df
        cols = df.columns

        col1, col2 = st.columns(2)
        with col1:
            if {"Distance", "Speed", "LapNumber"}.issubset(cols):
                st.plotly_chart(SpeedChart(df).render(), use_container_width=True)
        with col2:
            if {"Distance", "nGear", "LapNumber"}.issubset(cols):
                st.plotly_chart(GearChart(df).render(), use_container_width=True)

        if {"Distance", "Throttle", "Brake", "LapNumber"}.issubset(cols):
            st.plotly_chart(ThrottleBrakeChart(df).render(), use_container_width=True)
        if {"X", "Y", "Speed", "LapNumber"}.issubset(cols):
            st.plotly_chart(TrackMapChart(df).render(), use_container_width=True)

    def _render_raw_data(self) -> None:
        with st.expander("Raw telemetry data"):
            st.dataframe(self._lap_df, use_container_width=True)



class F1App:
    """Top-level orchestrator — ties sidebar, data, and dashboard together."""

    def __init__(self):
        st.set_page_config(page_title="F1 Telemetry Viewer", layout="wide")
        st.title("F1 Telemetry Viewer")

    def run(self) -> None:
        session = Sidebar.select_session()

        bundle = DataService.load_bundle(
            session.year, session.event, session.session_code, session.cache_dir
        )
        if bundle.telemetry.empty:
            st.error("No telemetry data available.")
            st.stop()

        selection = Sidebar.select_driver(bundle.telemetry, bundle.results)

        lap_df = get_multiple_laps_telemetry(
            bundle.telemetry, selection.driver, selection.laps
        )
        summary_df = get_lap_summary(
            bundle.telemetry, selection.driver, selection.laps
        )
        if lap_df.empty:
            st.warning("No telemetry data found for the selected laps.")
            st.stop()

        Dashboard(
            session=session,
            driver=selection.driver,
            lap_df=lap_df,
            summary_df=summary_df,
            results=bundle.results,
            selected_laps=selection.laps,
        ).render()


F1App().run()
