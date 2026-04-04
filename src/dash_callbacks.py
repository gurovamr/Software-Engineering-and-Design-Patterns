from datetime import date

import pandas as pd
from dash import Input, Output, State, no_update, callback_context, html
import plotly.graph_objects as go

from src.data_loading import load_session_quick, load_driver_telemetry, get_schedule_events
from src.telemetry_metrics import (
    get_available_drivers,
    get_driver_laps,
    get_multiple_laps_telemetry,
    get_lap_summary,
    get_fastest_laps_for_driver,
    get_results_table,
)
from src.visualization import (
    BaseChart,
    TeamColors,
    SpeedChart,
    ThrottleBrakeChart,
    GearChart,
    TrackMapChart,
    LapSummaryChart,
    PositionChart,
    DriverComparisonChart,
    TyreStrategyChart,
    TeamPaceChart,
    LapTimesDistributionChart,
    GearMapChart,
    KeyEventExtractor,
)
from src.auth_service import AuthService
from src.preload_service import DataLoader


class DashCallbacks:
    """Registers all Dash callbacks."""

    _session_cache: dict = {}



    @staticmethod
    def _empty_fig(title: str):
        return BaseChart.empty(title)

    @staticmethod
    def _prepare_telemetry(telemetry: pd.DataFrame) -> pd.DataFrame:
        """Cleans Driver and LapNumber columns."""
        df = telemetry.copy()
        df["Driver"] = df["Driver"].astype(str)
        df["LapNumber"] = pd.to_numeric(df["LapNumber"], errors="coerce")
        df = df[df["LapNumber"].notna()].copy()
        df["LapNumber"] = df["LapNumber"].astype(int)
        return df

    @classmethod
    def _empty_dashboard(cls):
        """Returns the empty dashboard tuple."""
        return (
            "Selected Laps: n/a",
            "Max Speed: n/a",
            "Samples: n/a",
            "Best Lap: n/a",
            cls._empty_fig("Lap Comparison"),
            [], [],
            cls._empty_fig("Speed"),
            cls._empty_fig("Gear"),
            cls._empty_fig("Throttle / Brake"),
            cls._empty_fig("Track Map"),
            cls._empty_fig("Gear Shifts on Track"),
        )

    @classmethod
    def _cache_bundle(cls, year, event, session_code, bundle):
        """Stores a bundle in the session cache."""
        key = f"{year}|{event}|{session_code}"
        cls._session_cache[key] = bundle
        return key

    @classmethod
    def _get_cached_bundle(cls, bundle_data):
        """Retrieves a bundle from the cache. Returns (bundle, telemetry_df) or (None, None)."""
        if not bundle_data:
            return None, None
        bundle = cls._session_cache.get(bundle_data.get("cache_key"))
        if bundle is None:
            return None, None
        if bundle.telemetry.empty:
            return bundle, pd.DataFrame()
        return bundle, cls._prepare_telemetry(bundle.telemetry)

    @staticmethod
    def _determine_default_driver(results_table, drivers):
        """Selects the default driver (first in results or first available)."""
        default = drivers[0] if drivers else None
        if not results_table.empty and "Driver" in results_table.columns:
            first = str(results_table["Driver"].iloc[0])
            if first in drivers:
                default = first
        return default

    @staticmethod
    def _format_results_columns(results_table):
        """Formats a results DataFrame as Dash DataTable columns."""
        return [{"name": c, "id": c} for c in results_table.columns]

    @staticmethod
    def _format_driver_options(drivers):
        """Formats a driver list as dropdown options."""
        return [{"label": d, "value": d} for d in drivers]

    @staticmethod
    def _format_lap_options(laps):
        """Formats lap numbers as dropdown options."""
        return [{"label": str(l), "value": int(l)} for l in laps]

    @staticmethod
    def _select_default_laps(telemetry_df, driver, all_laps):
        """Determines default laps (fastest 2 or first 2)."""
        default = get_fastest_laps_for_driver(telemetry_df, driver, top_n=2)
        if not default and all_laps:
            default = all_laps[:2]
        return [int(x) for x in default]

    @staticmethod
    def _compute_kpis(lap_df, summary_df, num_laps):
        """Computes the 4 KPI display strings."""
        laps_str = f"Selected Laps: {num_laps}"
        max_speed = (
            f"Max Speed: {lap_df['Speed'].max():.1f} km/h"
            if "Speed" in lap_df.columns else "Max Speed: n/a"
        )
        samples = f"Samples: {len(lap_df)}"
        best_lap = (
            f"Best Lap: {summary_df['LapTimeSeconds'].min():.3f} s"
            if not summary_df.empty and "LapTimeSeconds" in summary_df.columns
            else "Best Lap: n/a"
        )
        return laps_str, max_speed, samples, best_lap

    @classmethod
    def _build_lap_summary_chart(cls, summary_df, num_laps):
        """Builds the lap comparison chart."""
        if num_laps >= 2 and not summary_df.empty:
            return LapSummaryChart(summary_df).render()
        return cls._empty_fig("Lap Comparison")

    @classmethod
    def _build_all_charts(cls, lap_df, summary_df, num_laps):
        """Builds all dashboard charts."""
        chart_specs = [
            ({"Distance", "Speed", "LapNumber"}, SpeedChart, "Speed"),
            ({"Distance", "nGear", "LapNumber"}, GearChart, "Gear"),
            ({"Distance", "Throttle", "Brake", "LapNumber"}, ThrottleBrakeChart, "Throttle / Brake"),
            ({"X", "Y", "Speed", "LapNumber"}, TrackMapChart, "Track Map"),
            ({"X", "Y", "nGear"}, GearMapChart, "Gear Shifts on Track"),
        ]
        results = [cls._build_lap_summary_chart(summary_df, num_laps)]
        for cols_needed, chart_cls, fallback in chart_specs:
            if cols_needed.issubset(lap_df.columns):
                results.append(chart_cls(lap_df).render())
            else:
                results.append(cls._empty_fig(fallback))
        return tuple(results)

    

    _auth = AuthService()

    @classmethod
    def register(cls, app):

       

        @app.callback(
            Output("event-input", "options"),
            Output("event-input", "value"),
            Input("year-input", "value"),
        )
        def update_event_options(year):
            """Loads the event schedule for the selected year."""
            if not year:
                return [], None
            year = int(year)
            events = get_schedule_events(year)
            options = [{"label": e, "value": e} for e in events]
            default = events[0] if events else None
            return options, default

        @app.callback(
            Output("login-fav-driver", "options"),
            Input("login-name", "value"),
        )
        def populate_driver_suggestions(_):
            """Populates the favorite driver dropdown with known driver codes."""
            codes = cls._auth.get_all_driver_codes()
            popular = cls._auth.get_popular_drivers(limit=3)
            options = []
            for code in codes:
                label = f"{code} ★" if code in popular else code
                options.append({"label": label, "value": code})
            return options

        @app.callback(
            Output("user-store", "data"),
            Output("login-message", "children"),
            Input("btn-login", "n_clicks"),
            Input("btn-register", "n_clicks"),
            State("login-name", "value"),
            State("login-password", "value"),
            State("login-fav-driver", "value"),
            prevent_initial_call=True,
        )
        def handle_auth(login_clicks, register_clicks, name, password, fav_driver):
            """Handles login and registration."""
            if not name or not password:
                return no_update, "Please enter username and password."
            triggered = callback_context.triggered_id
            if triggered == "btn-register":
                ok, msg = cls._auth.register(name, password, fav_driver)
                if not ok:
                    return no_update, msg
                _, _, user = cls._auth.login(name, password)
                DataLoader.start()
                return user, msg
            else:
                ok, msg, user = cls._auth.login(name, password)
                if not ok:
                    return no_update, msg
                DataLoader.start()
                return user, ""

        @app.callback(
            Output("user-store", "data", allow_duplicate=True),
            Input("btn-logout", "n_clicks"),
            prevent_initial_call=True,
        )
        def handle_logout(n_clicks):
            """Clears user session on logout."""
            if n_clicks:
                return None
            return no_update

        @app.callback(
            Output("login-page", "style"),
            Output("dashboard-page", "style"),
            Output("user-greeting", "children"),
            Input("user-store", "data"),
        )
        def toggle_pages(user_data):
            """Shows login or dashboard page based on login state."""
            if user_data and user_data.get("name"):
                DataLoader.start()
                return (
                    {"display": "none"},
                    {"display": "block", "background": "#0d0d1a", "color": "#e0e0e0", "minHeight": "100vh"},
                    f"Hello, {user_data['name']}!",
                )
            return (
                {"maxWidth": "400px", "margin": "120px auto", "padding": "30px",
                 "background": "#1a1a2e", "borderRadius": "12px",
                 "border": "1px solid #333", "color": "#e0e0e0"},
                {"display": "none"},
                "",
            )

        @app.callback(
            Output("driver-dropdown", "value", allow_duplicate=True),
            Input("bundle-store", "data"),
            State("user-store", "data"),
            State("driver-dropdown", "options"),
            prevent_initial_call=True,
        )
        def suggest_favorite_driver(bundle_data, user_data, driver_options):
            """Pre-selects the user's favorite driver when a session is loaded."""
            if not user_data or not driver_options:
                return no_update
            fav = user_data.get("favorite_driver")
            if fav and any(opt["value"] == fav for opt in driver_options):
                return fav
            return no_update

    
        @app.callback(
            Output("sync-status", "children"),
            Output("sync-status", "style"),
            Output("sync-interval", "disabled"),
            Input("sync-interval", "n_intervals"),
            Input("user-store", "data"),
        )
        def update_sync_status(_, user_data):
            """Polls background data sync progress."""
            if not user_data or not user_data.get("name"):
                return "", {"display": "none"}, True
            status = DataLoader.get_status()
            if status["done"]:
                return (
                    "✓ All session data cached and ready.",
                    {"background": "#1a3a1a", "color": "#4ade80", "padding": "6px 16px",
                     "textAlign": "center", "fontSize": "0.85em"},
                    True,
                )
            if status["running"]:
                return (
                    f"⏳ {status['progress']}",
                    {"background": "#3a2a1a", "color": "#fbbf24", "padding": "6px 16px",
                     "textAlign": "center", "fontSize": "0.85em"},
                    False,
                )
            return "", {"display": "none"}, False

        # ── Telemetry callbacks ─────────────────────────────────────

        @app.callback(
            Output("bundle-store", "data"),
            Output("results-table", "columns"),
            Output("results-table", "data"),
            Output("driver-dropdown", "options"),
            Output("driver-dropdown", "value"),
            Output("session-header", "children"),
            Output("position-chart-graph", "figure"),
            Output("podium-p1-name", "children"),
            Output("podium-p1-team", "children"),
            Output("podium-p2-name", "children"),
            Output("podium-p2-team", "children"),
            Output("podium-p3-name", "children"),
            Output("podium-p3-team", "children"),
            Output("podium-fastest-name", "children"),
            Output("podium-fastest-team", "children"),
            Output("key-events-container", "children"),
            Output("compare-driver-dropdown", "options"),
            Output("tyre-strategy-graph", "figure"),
            Output("team-pace-graph", "figure"),
            Output("laptimes-dist-graph", "figure"),
            Input("load-button", "n_clicks"),
            State("year-input", "value"),
            State("event-input", "value"),
            State("session-input", "value"),
            State("user-store", "data"),
            prevent_initial_call=True,
        )
        def load_session(n_clicks, year, event, session_code, user_data):
            empty_pos = cls._empty_fig("Race Timeline – Position Chart")
            dash_empty = "—"
            try:
                bundle = load_session_quick(
                    year=year, event=event,
                    session_code=session_code,
                    cache_dir="cache",
                )
                cache_key = cls._cache_bundle(year, event, session_code, bundle)
                results_table = get_results_table(bundle.results)

                # Get drivers from results/laps (no telemetry needed)
                drivers = []
                if not bundle.results.empty and "Driver" in bundle.results.columns:
                    drivers = sorted(bundle.results["Driver"].dropna().astype(str).unique().tolist())
                elif not bundle.laps.empty and "Driver" in bundle.laps.columns:
                    drivers = sorted(bundle.laps["Driver"].dropna().astype(str).unique().tolist())

                empty_tyre = cls._empty_fig("Tyre Strategy")
                empty_pace = cls._empty_fig("Team Pace Comparison")
                empty_dist = cls._empty_fig("Lap Times Distribution")

                if not drivers:
                    return ({}, [], [], [], None, "No driver data available.",
                            empty_pos, dash_empty, "", dash_empty, "", dash_empty, "", dash_empty, "", [], [],
                            empty_tyre, empty_pace, empty_dist)

                # Use favorite driver as default if available
                fav = (user_data or {}).get("favorite_driver")
                if fav and fav in drivers:
                    default_driver = fav
                else:
                    default_driver = cls._determine_default_driver(results_table, drivers)

                # Position chart
                pos_fig = PositionChart(bundle.laps).render() if not bundle.laps.empty else empty_pos

                # Podium info (from results)
                p1_name, p1_team = dash_empty, ""
                p2_name, p2_team = dash_empty, ""
                p3_name, p3_team = dash_empty, ""
                fl_name, fl_team = dash_empty, ""
                res = bundle.results
                pos_col = "FinishPosition" if "FinishPosition" in res.columns else "Position"
                if not res.empty and pos_col in res.columns:
                    for pos in [1.0, 2.0, 3.0]:
                        row = res[pd.to_numeric(res[pos_col], errors="coerce") == pos]
                        if not row.empty:
                            r = row.iloc[0]
                            nm = str(r.get("FullName", r.get("Driver", "—")))
                            tm = str(r.get("Team", r.get("TeamName", "")))
                            if pos == 1.0:
                                p1_name, p1_team = nm, tm
                            elif pos == 2.0:
                                p2_name, p2_team = nm, tm
                            else:
                                p3_name, p3_team = nm, tm

                # Fastest lap
                if not bundle.laps.empty and "LapTime" in bundle.laps.columns:
                    valid = bundle.laps[bundle.laps["LapTime"].notna()]
                    if not valid.empty:
                        fl_row = valid.loc[valid["LapTime"].idxmin()]
                        fl_driver = str(fl_row.get("Driver", "?"))
                        fl_time = str(fl_row.get("LapTime", ""))
                        fl_team_val = str(fl_row.get("Team", ""))
                        fl_name = f"{fl_driver}  {fl_time}"
                        fl_team = fl_team_val

                # Key events
                events_data = KeyEventExtractor.extract(bundle.laps)
                event_badges = []
                for ev in events_data:
                    badge_color = "#e10600" if ev["type"] == "PIT" else "#555"
                    event_badges.append(html.Span(
                        f"{ev['driver']} {ev['type']} Lap {ev['lap']}",
                        style={
                            "background": badge_color, "color": "white",
                            "padding": "4px 10px", "borderRadius": "12px",
                            "fontSize": "0.8em", "whiteSpace": "nowrap",
                        },
                    ))
                if not event_badges:
                    event_badges = [html.Span("No events", style={"color": "#888"})]

                return (
                    {"cache_key": cache_key, "year": year, "event": event, "session": session_code},
                    cls._format_results_columns(results_table),
                    results_table.to_dict("records"),
                    cls._format_driver_options(drivers),
                    default_driver,
                    f"{year} {event} – {session_code}",
                    pos_fig,
                    p1_name, p1_team,
                    p2_name, p2_team,
                    p3_name, p3_team,
                    fl_name, fl_team,
                    event_badges,
                    cls._format_driver_options(drivers),
                    TyreStrategyChart(bundle.laps).render() if not bundle.laps.empty else empty_tyre,
                    TeamPaceChart(bundle.laps).render() if not bundle.laps.empty else empty_pace,
                    LapTimesDistributionChart(bundle.laps).render() if not bundle.laps.empty else empty_dist,
                )
            except Exception as e:
                return ({}, [], [], [], None, f"Error loading session: {e}",
                        empty_pos, dash_empty, "", dash_empty, "", dash_empty, "", dash_empty, "", [], [],
                        cls._empty_fig("Tyre Strategy"), cls._empty_fig("Team Pace"), cls._empty_fig("Lap Distribution"))

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
            if not driver:
                return [], []
            bundle, telemetry_df = cls._get_cached_bundle(bundle_data)
            if bundle is None:
                return [], []

            driver = str(driver)

            # Load telemetry on-demand for this driver from cached session
            if telemetry_df.empty or driver not in telemetry_df["Driver"].values:
                bd = bundle_data or {}
                year, event, sc = bd.get("year"), bd.get("event"), bd.get("session")
                if year and event and sc:
                    try:
                        driver_tel = load_driver_telemetry(
                            year, event, sc, driver, cache_dir="cache"
                        )
                        if not driver_tel.empty:
                            if bundle.telemetry.empty:
                                bundle.telemetry = driver_tel
                            else:
                                bundle.telemetry = pd.concat(
                                    [bundle.telemetry, driver_tel], ignore_index=True
                                )
                            telemetry_df = cls._prepare_telemetry(bundle.telemetry)
                    except Exception:
                        return [], []

            if telemetry_df.empty:
                return [], []

            laps = get_driver_laps(telemetry_df, driver)
            default_laps = cls._select_default_laps(telemetry_df, driver, laps)
            return cls._format_lap_options(laps), default_laps

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
            Output("gear-map-graph", "figure"),
            Input("driver-dropdown", "value"),
            Input("lap-dropdown", "value"),
            Input("bundle-store", "data"),
        )
        def update_dashboard(driver, selected_laps, bundle_data):
            if not driver or not selected_laps:
                return cls._empty_dashboard()

            bundle, telemetry_df = cls._get_cached_bundle(bundle_data)
            if bundle is None:
                return cls._empty_dashboard()

            driver = str(driver)
            selected_laps = [int(x) for x in selected_laps]
            lap_df = get_multiple_laps_telemetry(telemetry_df, driver, selected_laps)
            summary_df = get_lap_summary(telemetry_df, driver, selected_laps)

            if lap_df.empty:
                return (
                    f"Selected Laps: {len(selected_laps)}",
                    "Max Speed: n/a", "Samples: 0", "Best Lap: n/a",
                    *cls._empty_dashboard()[4:],
                )

            kpis = cls._compute_kpis(lap_df, summary_df, len(selected_laps))
            charts = cls._build_all_charts(lap_df, summary_df, len(selected_laps))

            return (
                *kpis,
                charts[0],
                cls._format_results_columns(summary_df),
                summary_df.to_dict("records"),
                *charts[1:],
            )

        
        @app.callback(
            Output("comparison-graph", "figure"),
            Output("comparison-section", "style"),
            Input("compare-driver-dropdown", "value"),
            Input("driver-dropdown", "value"),
            Input("bundle-store", "data"),
            prevent_initial_call=True,
        )
        def update_comparison(compare_driver, main_driver, bundle_data):
            hidden = {"display": "none"}
            card_visible = {
                "background": "#1a1a2e", "borderRadius": "10px", "padding": "16px",
                "border": "1px solid #333", "marginBottom": "20px",
            }

            if not compare_driver or not main_driver or compare_driver == main_driver:
                return cls._empty_fig("Driver Comparison"), hidden

            bd = bundle_data or {}
            year, event, sc = bd.get("year"), bd.get("event"), bd.get("session")
            if not year or not event or not sc:
                return cls._empty_fig("Driver Comparison"), hidden

            try:
                tel1 = load_driver_telemetry(year, event, sc, main_driver, cache_dir="cache")
                tel2 = load_driver_telemetry(year, event, sc, compare_driver, cache_dir="cache")
            except Exception:
                return cls._empty_fig("Driver Comparison"), hidden

            if tel1.empty or tel2.empty:
                return cls._empty_fig("Driver Comparison"), hidden

            # Use fastest lap for each driver
            def _fastest_lap_tel(tel_df, driver):
                df = tel_df[tel_df["Driver"].astype(str) == str(driver)]
                if df.empty or "LapTimeSeconds" not in df.columns:
                    return df
                valid = df[df["LapTimeSeconds"].notna()]
                if valid.empty:
                    return df
                best_lap = valid.loc[valid["LapTimeSeconds"].idxmin(), "LapNumber"]
                return df[df["LapNumber"] == best_lap].copy()

            t1 = _fastest_lap_tel(tel1, main_driver)
            t2 = _fastest_lap_tel(tel2, compare_driver)

            if t1.empty or t2.empty:
                return cls._empty_fig("Driver Comparison"), hidden

            # Get lap times for subtitle
            lt1 = str(t1["LapTime"].iloc[0]) if "LapTime" in t1.columns and t1["LapTime"].notna().any() else ""
            lt2 = str(t2["LapTime"].iloc[0]) if "LapTime" in t2.columns and t2["LapTime"].notna().any() else ""

            title = f"{year} {event} — {sc} Telemetry"
            fig = DriverComparisonChart(t1, t2, main_driver, compare_driver, title, lt1, lt2).render()
            return fig, card_visible