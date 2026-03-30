import pandas as pd
from dash import Input, Output, State, callback, no_update
import plotly.graph_objects as go
from io import StringIO

from src.data_loading import load_f1_data
from src.telemetry_metrics import (
    get_available_drivers,
    get_driver_laps,
    get_multiple_laps_telemetry,
    get_lap_summary,
    get_fastest_laps_for_driver,
    get_results_table,
)
from src.visualization import (
    plot_speed,
    plot_throttle_brake,
    plot_gear,
    plot_track_map,
    plot_lap_summary,
)

SESSION_CACHE = {}

def empty_fig(title: str):
    fig = go.Figure()
    fig.update_layout(title=title, height=350)
    return fig


def register_callbacks(app):
    @app.callback(
        Output("bundle-store", "data"),
        Output("results-table", "columns"),
        Output("results-table", "data"),
        Output("driver-dropdown", "options"),
        Output("driver-dropdown", "value"),
        Output("session-header", "children"),
        Input("load-button", "n_clicks"),
        State("year-input", "value"),
        State("event-input", "value"),
        State("session-input", "value"),
        prevent_initial_call=True,
    )
    def load_session(n_clicks, year, event, session_code):
        try:
            bundle = load_f1_data(
                year=year,
                event=event,
                session_code=session_code,
                cache_dir="cache",
                fastest_lap_only=False,
            )

            if bundle.telemetry.empty:
                return {}, [], [], [], None, "No telemetry data available."

            cache_key = f"{year}|{event}|{session_code}"
            SESSION_CACHE[cache_key] = bundle

            results_table = get_results_table(bundle.results)
            drivers = get_available_drivers(bundle.telemetry)

            default_driver = drivers[0] if drivers else None
            if not results_table.empty and "Driver" in results_table.columns:
                first_driver = str(results_table["Driver"].iloc[0])
                if first_driver in drivers:
                    default_driver = first_driver

            results_columns = [{"name": c, "id": c} for c in results_table.columns]
            results_data = results_table.to_dict("records")
            driver_options = [{"label": d, "value": d} for d in drivers]

            return (
                {"cache_key": cache_key, "year": year, "event": event, "session": session_code},
                results_columns,
                results_data,
                driver_options,
                default_driver,
                f"{year} {event} {session_code}",
            )
        except Exception as e:
            print("Error loading session:", repr(e))
            return {}, [], [], [], None, f"Error loading session: {e}"


    @app.callback(
        Output("driver-dropdown", "value", allow_duplicate=True),
        Input("results-table", "selected_rows"),
        State("results-table", "data"),
        prevent_initial_call=True,
    )
    def select_driver_from_table(selected_rows, rows):
        if not selected_rows or not rows:
            return no_update
        return rows[selected_rows[0]].get("Driver", no_update)

    @app.callback(
        Output("lap-dropdown", "options"),
        Output("lap-dropdown", "value"),
        Input("driver-dropdown", "value"),
        Input("bundle-store", "data"),
    )
    def update_lap_dropdown(driver, bundle_data):
        if not driver or not bundle_data:
            return [], []

        cache_key = bundle_data.get("cache_key")
        bundle = SESSION_CACHE.get(cache_key)

        if bundle is None or bundle.telemetry.empty:
            return [], []

        telemetry_df = bundle.telemetry.copy()
        telemetry_df["Driver"] = telemetry_df["Driver"].astype(str)
        telemetry_df["LapNumber"] = pd.to_numeric(telemetry_df["LapNumber"], errors="coerce")
        telemetry_df = telemetry_df[telemetry_df["LapNumber"].notna()].copy()
        telemetry_df["LapNumber"] = telemetry_df["LapNumber"].astype(int)

        driver = str(driver)
        laps = get_driver_laps(telemetry_df, driver)
        default_laps = get_fastest_laps_for_driver(telemetry_df, driver, top_n=2)

        if not default_laps and laps:
            default_laps = laps[:2]

        return (
            [{"label": str(l), "value": int(l)} for l in laps],
            [int(x) for x in default_laps],
        )
    
    @app.callback(
        Output("kpi-laps", "children"),
        Output("kpi-max-speed", "children"),
        Output("kpi-samples", "children"),
        Output("kpi-best-lap", "children"),
        Output("lap-summary-graph", "figure"),
        Output("lap-summary-table", "columns"),
        Output("lap-summary-table", "data"),
        Output("speed-graph", "figure"),
        Output("gear-graph", "figure"),
        Output("inputs-graph", "figure"),
        Output("trackmap-graph", "figure"),
        Input("driver-dropdown", "value"),
        Input("lap-dropdown", "value"),
        Input("bundle-store", "data"),
    )
    def update_dashboard(driver, selected_laps, bundle_data):
        if not driver or not selected_laps or not bundle_data:
            return (
                "Selected Laps: n/a",
                "Max Speed: n/a",
                "Samples: n/a",
                "Best Lap: n/a",
                empty_fig("Lap Comparison"),
                [],
                [],
                empty_fig("Speed"),
                empty_fig("Gear"),
                empty_fig("Throttle / Brake"),
                empty_fig("Track Map"),
            )

        cache_key = bundle_data.get("cache_key")
        bundle = SESSION_CACHE.get(cache_key)

        if bundle is None or bundle.telemetry.empty:
            return (
                "Selected Laps: n/a",
                "Max Speed: n/a",
                "Samples: 0",
                "Best Lap: n/a",
                empty_fig("Lap Comparison"),
                [],
                [],
                empty_fig("Speed"),
                empty_fig("Gear"),
                empty_fig("Throttle / Brake"),
                empty_fig("Track Map"),
            )

        telemetry_df = bundle.telemetry.copy()
        telemetry_df["Driver"] = telemetry_df["Driver"].astype(str)
        telemetry_df["LapNumber"] = pd.to_numeric(telemetry_df["LapNumber"], errors="coerce")
        telemetry_df = telemetry_df[telemetry_df["LapNumber"].notna()].copy()
        telemetry_df["LapNumber"] = telemetry_df["LapNumber"].astype(int)

        driver = str(driver)
        selected_laps = [int(x) for x in selected_laps]

        lap_df = get_multiple_laps_telemetry(telemetry_df, driver, selected_laps)
        summary_df = get_lap_summary(telemetry_df, driver, selected_laps)

        if lap_df.empty:
            return (
                f"Selected Laps: {len(selected_laps)}",
                "Max Speed: n/a",
                "Samples: 0",
                "Best Lap: n/a",
                empty_fig("Lap Comparison"),
                [],
                [],
                empty_fig("Speed"),
                empty_fig("Gear"),
                empty_fig("Throttle / Brake"),
                empty_fig("Track Map"),
            )

        max_speed = f"{lap_df['Speed'].max():.1f} km/h" if "Speed" in lap_df.columns else "n/a"
        best_lap = (
            f"{summary_df['LapTimeSeconds'].min():.3f} s"
            if not summary_df.empty and "LapTimeSeconds" in summary_df.columns
            else "n/a"
        )

        lap_summary_fig = (
            plot_lap_summary(summary_df)
            if len(selected_laps) >= 2 and not summary_df.empty
            else empty_fig("Lap Comparison")
        )
        speed_fig = (
            plot_speed(lap_df)
            if {"Distance", "Speed", "LapNumber"}.issubset(lap_df.columns)
            else empty_fig("Speed")
        )
        gear_fig = (
            plot_gear(lap_df)
            if {"Distance", "nGear", "LapNumber"}.issubset(lap_df.columns)
            else empty_fig("Gear")
        )
        inputs_fig = (
            plot_throttle_brake(lap_df)
            if {"Distance", "Throttle", "Brake", "LapNumber"}.issubset(lap_df.columns)
            else empty_fig("Throttle / Brake")
        )
        track_fig = (
            plot_track_map(lap_df)
            if {"X", "Y", "Speed", "LapNumber"}.issubset(lap_df.columns)
            else empty_fig("Track Map")
        )

        summary_columns = [{"name": c, "id": c} for c in summary_df.columns]
        summary_data = summary_df.to_dict("records")

        return (
            f"Selected Laps: {len(selected_laps)}",
            f"Max Speed: {max_speed}",
            f"Samples: {len(lap_df)}",
            f"Best Lap: {best_lap}",
            lap_summary_fig,
            summary_columns,
            summary_data,
            speed_fig,
            gear_fig,
            inputs_fig,
            track_fig,
        )