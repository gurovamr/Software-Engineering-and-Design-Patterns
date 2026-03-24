from pathlib import Path
import sys

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
    get_results_table
)
from src.visualization import (
    plot_speed,
    plot_throttle_brake,
    plot_gear,
    plot_track_map,
    plot_lap_summary
)

st.set_page_config(page_title="F1 Telemetry Viewer", layout="wide")
st.title("F1 Telemetry Viewer")

SESSION_OPTIONS = ["R", "Q", "FP1", "FP2", "FP3", "S", "SQ"]


@st.cache_data(show_spinner=False)
def cached_load_bundle(year: int, event: str, session_code: str, cache_dir: str):
    return load_f1_data(
        year=year,
        event=event,
        session_code=session_code,
        cache_dir=cache_dir,
        fastest_lap_only=False
    )


@st.cache_data(show_spinner=False)
def cached_available_events(year: int, session_code: str, cache_dir: str):
    return get_events_with_available_laps(
        year=year,
        session_code=session_code,
        cache_dir=cache_dir
    )


@st.cache_data(show_spinner=False)
def cached_schedule_events(year: int):
    return get_schedule_events(year)


with st.sidebar:
    st.header("Session Selection")
    year = st.number_input("Year", min_value=2018, max_value=2026, value=2024, step=1)
    session_code = st.selectbox("Session", SESSION_OPTIONS, index=1)
    cache_dir = st.text_input("Cache directory", value="cache")

with st.spinner("Checking which events have lap data for this year/session..."):
    available_events = cached_available_events(year, session_code, cache_dir)
schedule_events = cached_schedule_events(year)

with st.sidebar:
    if available_events:
        default_event = "Monza" if "Monza" in available_events else available_events[0]
        event = st.selectbox(
            "Race / Event",
            options=available_events,
            index=available_events.index(default_event)
        )
        st.caption(f"{len(available_events)} events found with lap data.")
    elif schedule_events:
        default_event = "Monza" if "Monza" in schedule_events else schedule_events[0]
        event = st.selectbox(
            "Race / Event",
            options=schedule_events,
            index=schedule_events.index(default_event)
        )
        st.caption("No events could be verified with lap telemetry right now. Showing full race schedule.")
    else:
        st.warning("No events with lap data were detected. Use manual input.")
        event = st.text_input("Race / Event", value="Monza")

bundle = cached_load_bundle(year, event, session_code, cache_dir)

if bundle.telemetry.empty:
    st.error("No telemetry data available.")
    st.stop()

drivers = get_available_drivers(bundle.telemetry)
if not drivers:
    st.error("No drivers found in telemetry.")
    st.stop()

default_driver = drivers[0]
if not bundle.results.empty and "Driver" in bundle.results.columns:
    result_drivers = bundle.results["Driver"].dropna().tolist()
    if result_drivers and result_drivers[0] in drivers:
        default_driver = result_drivers[0]


with st.sidebar:
    st.header("Telemetry Selection")

    driver = st.selectbox("Driver", drivers, index=drivers.index(default_driver) if default_driver in drivers else 0)

    available_laps = get_driver_laps(bundle.telemetry, driver)
    default_laps = get_fastest_laps_for_driver(bundle.telemetry, driver, top_n=2)
    if not default_laps and available_laps:
        default_laps = available_laps[:2]

    selected_laps = st.multiselect(
        "Laps to compare",
        options=available_laps,
        default=default_laps
    )

if not selected_laps:
    st.warning("Please select at least one lap.")
    st.stop()

lap_df = get_multiple_laps_telemetry(bundle.telemetry, driver, selected_laps)
summary_df = get_lap_summary(bundle.telemetry, driver, selected_laps)

if lap_df.empty:
    st.warning("No telemetry data found for the selected laps.")
    st.stop()

# Display session and driver info
st.subheader(f"{year} {event} {session_code} — {driver}")

c1, c2, c3 = st.columns(3)
c1.metric("Selected Laps", len(selected_laps))
c2.metric("Max Speed", f"{lap_df['Speed'].max():.1f} km/h" if "Speed" in lap_df.columns else "n/a")
c3.metric("Telemetry Samples", len(lap_df))

# Results table
results_table = get_results_table(bundle.results)

st.subheader("Driver Ranking / Classification")
st.dataframe(results_table, use_container_width=True, hide_index=True)

# Lap Comparison
st.subheader("Lap Comparison")
if len(selected_laps) >= 2 and not summary_df.empty:
    st.plotly_chart(plot_lap_summary(summary_df), use_container_width=True)
else:
    if not summary_df.empty:
        best_row = summary_df.iloc[0]
        st.metric("Lap Time", f"{best_row['LapTimeSeconds']:.3f} s")

st.subheader("Lap Summary")
if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
else:
    st.info("No lap summary available.")

# Telemetry Plots
st.subheader("Telemetry Analysis")
col1, col2 = st.columns(2)

with col1:
    if {"Distance", "Speed", "LapNumber"}.issubset(lap_df.columns):
        st.plotly_chart(plot_speed(lap_df), use_container_width=True)

with col2:
    if {"Distance", "nGear", "LapNumber"}.issubset(lap_df.columns):
        st.plotly_chart(plot_gear(lap_df), use_container_width=True)

if {"Distance", "Throttle", "Brake", "LapNumber"}.issubset(lap_df.columns):
    st.plotly_chart(plot_throttle_brake(lap_df), use_container_width=True)

if {"X", "Y", "Speed", "LapNumber"}.issubset(lap_df.columns):
    st.plotly_chart(plot_track_map(lap_df), use_container_width=True)

with st.expander("Raw telemetry data"):
    st.dataframe(lap_df, use_container_width=True)