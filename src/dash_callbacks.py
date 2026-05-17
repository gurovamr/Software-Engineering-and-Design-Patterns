import pandas as pd
from dash import ClientsideFunction, Input, Output, State, no_update, callback_context, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

from src.database import F1TrackQuery, TrackRepository
from src.session_service import SessionService
from src.telemetry_metrics import (
    get_available_drivers,
    get_driver_laps,
    get_multiple_laps_telemetry,
    get_lap_summary,
    get_fastest_laps_for_driver,
    get_results_table,
    PitStopExtractor,
)
from src.visualization import (
    BaseChart,
    SpeedChart,
    ThrottleBrakeChart,
    GearChart,
    LapSummaryChart,
    PositionChart,
    TyreStrategyChart,
    TeamPaceChart,
    LapTimesDistributionChart,
    F1ColorPalette,
)
from src.auth_service import AuthService, DriverService
from src.preload_service import DataLoader

DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "f1.sqlite")


class DashboardCallbackRegistry:
    """
    Registers all Dash callbacks.

    Pattern: Dependency Injection - AuthService, DriverRepository, DataLoader
             are injected, not hardcoded.
    """

    def __init__(
        self,
        auth_service: AuthService,
        driver_service: DriverService,
        data_loader: DataLoader,
        session_service: SessionService,
    ) -> None:
        self._auth = auth_service
        self._driver_repo = driver_service
        self._loader = data_loader
        self._session_service = session_service
        self._session_cache: dict = {}



    @staticmethod
    def _empty_fig(title: str):
        return BaseChart.empty_figure(title)

    @staticmethod
    def _clean_telemetry_dataframe(telemetry: pd.DataFrame) -> pd.DataFrame:
        """Cleans Driver and LapNumber columns."""
        if telemetry.empty or not {"Driver", "LapNumber"}.issubset(telemetry.columns):
            return pd.DataFrame()
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
            cls._empty_fig("Lap Times for Selected Drivers"),
            cls._empty_fig("Speed"),
            cls._empty_fig("Gear"),
            cls._empty_fig("Throttle / Brake"),
            cls._empty_fig("Track Map"),
            cls._empty_fig("Gear Shifts on Track"),
            None,
            {"display": "none"},
        )

    def _store_session_bundle(self, year, event, session_code, bundle):
        """Stores a bundle in the session cache."""
        key = f"{year}|{event}|{session_code}"
        self._session_cache[key] = bundle
        return key

    def _retrieve_cached_bundle(self, bundle_data):
        """Retrieves a bundle from the cache. Returns (bundle, telemetry_df) or (None, None)."""
        if not bundle_data:
            return None, None
        bundle = self._session_cache.get(bundle_data.get("cache_key"))
        if bundle is None:
            return None, None
        if bundle.telemetry.empty:
            return bundle, pd.DataFrame()
        return bundle, self._clean_telemetry_dataframe(bundle.telemetry)

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
    def _to_datatable_columns(results_table):
        """Formats a results DataFrame as Dash DataTable columns."""
        return [{"name": c, "id": c} for c in results_table.columns]

    @staticmethod
    def _to_driver_dropdown_options(drivers):
        """Formats a driver list as dropdown options."""
        return [{"label": d, "value": d} for d in drivers]

    @staticmethod
    def _to_lap_dropdown_options(laps):
        """Formats lap numbers as dropdown options."""
        return [{"label": str(l), "value": int(l)} for l in laps]

    @staticmethod
    def _select_default_laps(telemetry_df, driver, all_laps):
        """Determines the default lap (fastest lap, with first lap as fallback)."""
        default = get_fastest_laps_for_driver(telemetry_df, driver, top_n=1)
        if not default and all_laps:
            default = all_laps[:1]
        return [int(x) for x in default]

    @staticmethod
    def _drivers_from_selected_rows(selected_rows, rows, fallback=None):
        drivers: list[str] = []
        if rows and selected_rows:
            for idx in selected_rows[:3]:
                if 0 <= int(idx) < len(rows):
                    driver = rows[int(idx)].get("Driver")
                    if driver and str(driver) not in drivers:
                        drivers.append(str(driver))
        if not drivers and fallback:
            drivers.append(str(fallback))
        return drivers

    @staticmethod
    def _summary_for_drivers(telemetry_df, drivers):
        frames = []
        for driver in drivers:
            laps = get_driver_laps(telemetry_df, driver)
            summary = get_lap_summary(telemetry_df, driver, laps)
            if summary.empty:
                continue
            summary.insert(0, "Driver", str(driver))
            frames.append(summary)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @staticmethod
    def _fastest_telemetry_for_drivers(telemetry_df, drivers):
        frames = []
        for driver in drivers:
            laps = get_fastest_laps_for_driver(telemetry_df, driver, top_n=1)
            if not laps:
                available = get_driver_laps(telemetry_df, driver)
                laps = available[:1]
            if not laps:
                continue
            lap = int(laps[0])
            df = get_multiple_laps_telemetry(telemetry_df, driver, [lap])
            if df.empty:
                continue
            df = df.copy()
            df["TraceLabel"] = f"{driver} L{lap}"
            frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @staticmethod
    def _summary_from_telemetry(lap_df):
        if lap_df.empty or not {"Driver", "LapNumber"}.issubset(lap_df.columns):
            return pd.DataFrame()
        aggregations = {"LapTimeSeconds": ("LapTimeSeconds", "first")}
        if "Speed" in lap_df.columns:
            aggregations.update(MaxSpeed=("Speed", "max"), MeanSpeed=("Speed", "mean"))
        if "Throttle" in lap_df.columns:
            aggregations.update(MeanThrottle=("Throttle", "mean"))
        if "Brake" in lap_df.columns:
            aggregations.update(BrakeEvents=("Brake", lambda s: int((s > 0).sum()) if s.notna().any() else 0))
        return (
            lap_df.groupby(["Driver", "LapNumber"], as_index=False)
            .agg(**aggregations)
            .sort_values(["Driver", "LapNumber"])
        )

    @staticmethod
    def _format_lap_selection_table(summary_df):
        if summary_df.empty:
            return pd.DataFrame()
        out = summary_df.copy()
        cols = [c for c in ["Driver", "LapNumber", "LapTimeSeconds", "MaxSpeed", "MeanSpeed"] if c in out.columns]
        out = out[cols].copy()
        for col in ["LapTimeSeconds", "MaxSpeed", "MeanSpeed"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").round(3)
        if "LapTimeSeconds" in out.columns:
            out = out.sort_values(["Driver", "LapTimeSeconds", "LapNumber"])
        else:
            out = out.sort_values(["Driver", "LapNumber"])
        return out.reset_index(drop=True)

    @classmethod
    def _top_lap_table_for_driver(cls, summary_df, driver, limit=10):
        if summary_df.empty or "Driver" not in summary_df.columns:
            return pd.DataFrame()
        table = cls._format_lap_selection_table(summary_df)
        table = table[table["Driver"].astype(str) == str(driver)].copy()
        if limit is not None:
            table = table.head(limit)
        return table.reset_index(drop=True)

    @staticmethod
    def _lap_table_columns(table):
        hidden = {"Driver"}
        return [{"name": c, "id": c} for c in table.columns if c not in hidden]

    @staticmethod
    def _default_lap_table_rows(lap_table, per_driver=5):
        if lap_table.empty or not {"Driver", "LapNumber"}.issubset(lap_table.columns):
            return []
        selected = []
        sort_cols = ["Driver"]
        if "LapTimeSeconds" in lap_table.columns:
            sort_cols.append("LapTimeSeconds")
        sort_cols.append("LapNumber")
        ordered = lap_table.sort_values(sort_cols)
        for driver, group in ordered.groupby("Driver", sort=False):
            selected.extend(group.head(per_driver).index.astype(int).tolist())
        return sorted(selected)

    @staticmethod
    def _selected_lap_rows_to_df(rows, selected_rows):
        if not rows:
            return pd.DataFrame()
        if selected_rows:
            selected = [rows[int(idx)] for idx in selected_rows if 0 <= int(idx) < len(rows)]
        else:
            selected = rows
        df = pd.DataFrame(selected)
        if not df.empty and "LapNumber" in df.columns:
            df["LapNumber"] = pd.to_numeric(df["LapNumber"], errors="coerce").astype("Int64")
        return df

    @staticmethod
    def _telemetry_from_lap_rows(telemetry_df, lap_rows_df):
        frames = []
        if lap_rows_df.empty:
            return pd.DataFrame()
        for _, row in lap_rows_df.dropna(subset=["Driver", "LapNumber"]).iterrows():
            driver = str(row["Driver"])
            lap = int(row["LapNumber"])
            df = get_multiple_laps_telemetry(telemetry_df, driver, [lap])
            if df.empty:
                continue
            df = df.copy()
            df["TraceLabel"] = f"{driver} L{lap}"
            frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @staticmethod
    def _track_telemetry_for_drivers(telemetry_df, drivers, lap_values):
        frames = []
        for idx, driver in enumerate(drivers[:3]):
            lap = lap_values[idx] if idx < len(lap_values) else None
            candidate_laps = []
            lap_number = pd.to_numeric(lap, errors="coerce")
            if pd.notna(lap_number):
                candidate_laps.append(int(lap_number))
            default = get_fastest_laps_for_driver(telemetry_df, driver, top_n=1)
            if default and int(default[0]) not in candidate_laps:
                candidate_laps.append(int(default[0]))
            if not candidate_laps:
                continue
            df = pd.DataFrame()
            selected_lap = None
            for candidate_lap in candidate_laps:
                df = get_multiple_laps_telemetry(telemetry_df, driver, [candidate_lap])
                if not df.empty:
                    selected_lap = candidate_lap
                    break
            if df.empty:
                continue
            df = df.copy()
            df["TraceLabel"] = f"{driver} L{selected_lap}"
            frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @staticmethod
    def _track_store_data(track_df):
        if track_df is None or track_df.empty:
            return []
        columns = [
            "TraceLabel", "Driver", "LapNumber", "Distance",
            "Speed", "Throttle", "Brake", "nGear", "X", "Y",
        ]
        safe = track_df[[col for col in columns if col in track_df.columns]].copy()
        return safe.astype(object).where(pd.notna(safe), None).to_dict("records")

    @staticmethod
    def _track_store_frame(data):
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    @staticmethod
    def _track_hover_distance(hover_data):
        if not hover_data or not hover_data.get("points"):
            return None
        point = hover_data["points"][0]
        customdata = point.get("customdata") or []
        if len(customdata) >= 4:
            return pd.to_numeric(customdata[3], errors="coerce")
        return pd.to_numeric(point.get("x"), errors="coerce")

    @staticmethod
    def _track_hover_columns(df):
        columns = ["TraceLabel", "Driver", "LapNumber", "Distance", "Speed", "Throttle", "Brake", "nGear"]
        out = df.copy()
        for col in columns:
            if col not in out.columns:
                out[col] = None
        return out, columns

    @staticmethod
    def _track_hover_text(row):
        driver = row.get("Driver", "")
        lap = row.get("LapNumber", "")
        distance = pd.to_numeric(row.get("Distance"), errors="coerce")
        speed = pd.to_numeric(row.get("Speed"), errors="coerce")
        throttle = pd.to_numeric(row.get("Throttle"), errors="coerce")
        brake = row.get("Brake", "")
        gear = pd.to_numeric(row.get("nGear"), errors="coerce")

        parts = [str(row.get("TraceLabel", driver))]
        if pd.notna(lap):
            parts.append(f"Lap {int(lap)}")
        if pd.notna(distance):
            parts.append(f"{distance:.1f} m")
        if pd.notna(speed):
            parts.append(f"Speed {speed:.1f} km/h")
        if pd.notna(throttle):
            parts.append(f"Throttle {throttle:.0f}%")
        if pd.notna(brake) and str(brake) != "":
            parts.append(f"Brake {brake}")
        if pd.notna(gear):
            parts.append(f"Gear {int(gear)}")
        return "<br>".join(parts)

    @staticmethod
    def _track_hover_badge(row):
        distance = pd.to_numeric(row.get("Distance"), errors="coerce")
        speed = pd.to_numeric(row.get("Speed"), errors="coerce")
        throttle = pd.to_numeric(row.get("Throttle"), errors="coerce")
        brake = row.get("Brake", "")
        gear = pd.to_numeric(row.get("nGear"), errors="coerce")
        parts = [str(row.get("TraceLabel", ""))]
        if pd.notna(distance):
            parts.append(f"{distance:.0f} m")
        if pd.notna(speed):
            parts.append(f"S {speed:.0f} km/h")
        if pd.notna(throttle):
            parts.append(f"T {throttle:.0f}%")
        brake_text = str(brake).strip().lower()
        if brake_text in {"true", "1", "1.0"}:
            parts.append("Brake")
        else:
            brake_value = pd.to_numeric(brake, errors="coerce")
            if pd.notna(brake_value) and float(brake_value) > 0:
                parts.append(f"B {brake_value:.0f}")
        if pd.notna(gear):
            parts.append(f"G{int(gear)}")
        return "<br>".join(parts)

    @classmethod
    def _nearest_track_points(cls, track_df, labels, hover_distance):
        if hover_distance is None or pd.isna(hover_distance) or "Distance" not in track_df.columns:
            return {}
        points = {}
        for label in labels:
            df = track_df[track_df["TraceLabel"].astype(str) == str(label)].copy()
            if df.empty:
                continue
            distances = pd.to_numeric(df["Distance"], errors="coerce")
            if distances.isna().all():
                continue
            idx = (distances - float(hover_distance)).abs().idxmin()
            points[label] = df.loc[idx]
        return points

    @staticmethod
    def _empty_track_grid(title):
        return BaseChart.empty_figure(title, height=420)

    @classmethod
    def _build_speed_track_grid(cls, track_df, hover_distance=None):
        if track_df.empty or not {"X", "Y", "Speed", "TraceLabel"}.issubset(track_df.columns):
            return cls._empty_track_grid("Track Map colored by Speed")
        labels = list(track_df["TraceLabel"].dropna().astype(str).unique())[:3]
        if not labels:
            return cls._empty_track_grid("Track Map colored by Speed")
        revision = "track-map|" + "|".join(labels)
        fig = make_subplots(rows=1, cols=len(labels), subplot_titles=labels)
        hover_points = cls._nearest_track_points(track_df, labels, hover_distance)
        for col, label in enumerate(labels, start=1):
            df = track_df[track_df["TraceLabel"].astype(str) == label]
            df, hover_cols = cls._track_hover_columns(df)
            df["HoverText"] = df.apply(cls._track_hover_text, axis=1)
            fig.add_trace(
                go.Scatter(
                    x=df["X"],
                    y=df["Y"],
                    mode="markers",
                    marker=dict(size=5, color=df["Speed"], coloraxis="coloraxis"),
                    customdata=df[hover_cols],
                    hovertext=df["HoverText"],
                    hoverinfo="none",
                    hovertemplate=None,
                    name=label,
                    showlegend=False,
                ),
                row=1,
                col=col,
            )
            if label in hover_points:
                point = hover_points[label]
                text = cls._track_hover_text(point)
                badge = cls._track_hover_badge(point)
                fig.add_trace(
                    go.Scatter(
                        x=[point["X"]],
                        y=[point["Y"]],
                        mode="markers+text",
                        marker=dict(
                            size=14,
                            color="rgba(255,255,255,0)",
                            line=dict(color="#ffffff", width=3),
                        ),
                        text=[badge],
                        textposition="top center",
                        textfont=dict(color="#ffffff", size=10),
                        hovertext=[text],
                        hoverinfo="skip",
                        hovertemplate=None,
                        name=f"{label} hover",
                        showlegend=False,
                    ),
                    row=1,
                    col=col,
                )
            fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False, row=1, col=col)
            fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, scaleanchor=f"x{col if col > 1 else ''}", row=1, col=col)
        fig.update_layout(
            title=dict(text="Track Map colored by Speed", font=dict(color="#e0e0e0", size=14)),
            height=420,
            paper_bgcolor="#1a1a2e",
            plot_bgcolor="#1a1a2e",
            font=dict(color="#e0e0e0"),
            coloraxis=dict(colorscale="Turbo", colorbar=dict(title="km/h")),
            hovermode="closest",
            hoverdistance=20,
            uirevision=revision,
            datarevision=revision,
            autosize=True,
            margin=dict(l=15, r=15, t=60, b=25),
        )
        return fig

    @classmethod
    def _build_gear_track_grid(cls, track_df, hover_distance=None):
        if track_df.empty or not {"X", "Y", "nGear", "TraceLabel"}.issubset(track_df.columns):
            return cls._empty_track_grid("Gear Shifts on Track")
        df = track_df.copy()
        df["nGear"] = pd.to_numeric(df["nGear"], errors="coerce")
        df = df[df["nGear"] >= 1]
        if df.empty:
            return cls._empty_track_grid("Gear Shifts on Track")
        labels = list(df["TraceLabel"].dropna().astype(str).unique())[:3]
        if not labels:
            return cls._empty_track_grid("Gear Shifts on Track")
        revision = "gear-map|" + "|".join(labels)
        fig = make_subplots(rows=1, cols=len(labels), subplot_titles=labels)
        hover_points = cls._nearest_track_points(df, labels, hover_distance)
        for col, label in enumerate(labels, start=1):
            label_df = df[df["TraceLabel"].astype(str) == label]
            label_df, hover_cols = cls._track_hover_columns(label_df)
            label_df["HoverText"] = label_df.apply(cls._track_hover_text, axis=1)
            for gear in sorted(label_df["nGear"].dropna().unique()):
                gear_int = int(gear)
                gd = label_df[label_df["nGear"] == gear]
                fig.add_trace(
                    go.Scatter(
                        x=gd["X"],
                        y=gd["Y"],
                        mode="markers",
                        marker=dict(color=F1ColorPalette.get_gear_color(gear_int), size=4),
                        name=f"Gear {gear_int}",
                        showlegend=(col == 1),
                        customdata=gd[hover_cols],
                        hovertext=gd["HoverText"],
                        hoverinfo="none",
                        hovertemplate=None,
                    ),
                    row=1,
                    col=col,
                )
            if label in hover_points:
                point = hover_points[label]
                text = cls._track_hover_text(point)
                badge = cls._track_hover_badge(point)
                fig.add_trace(
                    go.Scatter(
                        x=[point["X"]],
                        y=[point["Y"]],
                        mode="markers+text",
                        marker=dict(
                            size=14,
                            color="rgba(255,255,255,0)",
                            line=dict(color="#ffffff", width=3),
                        ),
                        text=[badge],
                        textposition="top center",
                        textfont=dict(color="#ffffff", size=10),
                        hovertext=[text],
                        hoverinfo="skip",
                        hovertemplate=None,
                        name=f"{label} hover",
                        showlegend=False,
                    ),
                    row=1,
                    col=col,
                )
            fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False, row=1, col=col)
            fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, scaleanchor=f"x{col if col > 1 else ''}", row=1, col=col)
        fig.update_layout(
            title=dict(text="Gear Shifts on Track", font=dict(color="#e0e0e0", size=14)),
            height=420,
            paper_bgcolor="#1a1a2e",
            plot_bgcolor="#1a1a2e",
            font=dict(color="#e0e0e0"),
            legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"),
            hovermode="closest",
            hoverdistance=20,
            uirevision=revision,
            datarevision=revision,
            autosize=True,
            margin=dict(l=15, r=15, t=60, b=55),
        )
        return fig

    @staticmethod
    def _compute_kpi_strings(lap_df, summary_df, num_laps):
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
        if num_laps >= 1 and not summary_df.empty:
            return LapSummaryChart(summary_df).render()
        return cls._empty_fig("Lap Times for Selected Drivers")

    @classmethod
    def _build_all_charts(
        cls,
        lap_df,
        summary_df,
        num_laps,
        track_df=None,
        speed_hover_distance=None,
        gear_hover_distance=None,
    ):
        """Builds all dashboard charts."""
        results = [cls._build_lap_summary_chart(summary_df, len(summary_df))]

        if {"Distance", "Speed", "LapNumber"}.issubset(lap_df.columns):
            results.append(SpeedChart(lap_df).render())
        else:
            results.append(cls._empty_fig("Speed"))

        if {"Distance", "nGear", "LapNumber"}.issubset(lap_df.columns):
            results.append(GearChart(lap_df).render())
        else:
            results.append(cls._empty_fig("Gear"))

        if {"Distance", "Throttle", "Brake", "LapNumber"}.issubset(lap_df.columns):
            results.append(ThrottleBrakeChart(lap_df).render())
        else:
            results.append(cls._empty_fig("Throttle / Brake"))

        if track_df is None:
            track_df = lap_df

        results.append(cls._build_speed_track_grid(track_df, hover_distance=speed_hover_distance))
        results.append(cls._build_gear_track_grid(track_df, hover_distance=gear_hover_distance))

        return tuple(results)

    def register(self, app):
        """Registers all Dash callbacks on the given app instance."""
        # Capture injected dependencies for use inside closures
        auth = self._auth
        driver_repo = self._driver_repo
        loader = self._loader
        session_service = self._session_service
        # Capture helpers for use inside nested callback functions
        instance = self
        cls = type(self)

        app.clientside_callback(
            ClientsideFunction(namespace="sedpTrackHover", function_name="sync"),
            Output("track-hover-sync-store", "data"),
            Input("trackmap-graph", "hoverData"),
            Input("gear-map-graph", "hoverData"),
            prevent_initial_call=True,
        )

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
            # Cache-first: serve from local DB, only hit network if empty
            track_repo = TrackRepository(DB_PATH)
            events = track_repo.get_events(year)
            if not events:
                events = F1TrackQuery.from_schedule(year)
                if events:
                    track_repo.upsert_event_names(year, events)
            options = [{"label": e, "value": e} for e in events]
            default = events[0] if events else None
            return options, default

        @app.callback(
            Output("login-fav-driver", "options"),
            Output("login-fav-driver", "disabled"),
            Output("login-fav-driver", "placeholder"),
            Output("driver-options-status", "children"),
            Output("driver-options-status", "style"),
            Input("driver-options-loader", "n_intervals"),
        )
        def populate_driver_suggestions(n_intervals):
            """Populates the favorite driver dropdown with known driver codes."""
            status_style = {"color": "#888", "fontSize": "0.8em", "marginBottom": "16px"}
            if n_intervals is None:
                return [], True, "Loading drivers...", "Loading driver list...", status_style

            codes = driver_repo.get_all_driver_codes()
            if len(codes) < 10:
                codes = driver_repo.refresh_known_driver_codes(min_count=10)
            popular = driver_repo.get_popular_drivers(limit=3)
            options = []
            for code in codes:
                label = f"{code} ★" if code in popular else code
                options.append({"label": label, "value": code})
            if options:
                if len(options) < 10:
                    return (
                        options,
                        False,
                        "Select driver...",
                        f"Only {len(options)} cached drivers available. FastF1 refresh did not complete.",
                        {**status_style, "color": "#fbbf24"},
                    )
                return (
                    options,
                    False,
                    "Select driver...",
                    f"{len(options)} drivers loaded.",
                    {**status_style, "color": "#4ade80"},
                )
            return (
                [],
                True,
                "Drivers unavailable",
                "Driver list could not be loaded yet. You can still register without a favorite driver.",
                {**status_style, "color": "#fbbf24"},
            )

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
                ok, msg = auth.register(name, password, fav_driver)
                if not ok:
                    return no_update, msg
                _, _, user = auth.login(name, password)
                return user, msg
            else:
                ok, msg, user = auth.login(name, password)
                if not ok:
                    return no_update, msg
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
            status = loader.get_sync_status()
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
            # Check for error state in progress message
            if isinstance(status.get("progress"), str) and status["progress"].startswith("Error:"):
                return (
                    status["progress"],
                    {"background": "#3a1a1a", "color": "#ef4444", "padding": "6px 16px",
                     "textAlign": "center", "fontSize": "0.85em"},
                    True,
                )
            return "", {"display": "none"}, False

        # ── Telemetry callbacks ─────────────────────────────────────

        @app.callback(
            Output("session-load-status", "children", allow_duplicate=True),
            Output("session-load-status", "style", allow_duplicate=True),
            Output("full-event-load-status", "children", allow_duplicate=True),
            Output("full-event-load-status", "style", allow_duplicate=True),
            Output("telemetry-load-status", "children", allow_duplicate=True),
            Output("telemetry-load-status", "style", allow_duplicate=True),
            Output("telemetry-loading-banner", "style", allow_duplicate=True),
            Input("year-input", "value"),
            Input("event-input", "value"),
            Input("session-input", "value"),
            prevent_initial_call=True,
        )
        def reset_load_messages(_, __, ___):
            session_style = {"display": "none"}
            small_style = {"color": "#888", "fontSize": "0.8em", "marginTop": "8px"}
            telemetry_style = {"color": "#888", "fontSize": "0.8em", "marginTop": "6px"}
            return (
                "",
                session_style,
                "Full event loads all available session overviews for this Grand Prix.",
                small_style,
                "",
                telemetry_style,
                {"display": "none"},
            )

        @app.callback(
            Output("full-event-load-status", "children"),
            Output("full-event-load-status", "style"),
            Input("load-full-event-button", "n_clicks"),
            State("year-input", "value"),
            State("event-input", "value"),
            prevent_initial_call=True,
            running=[
                (
                    Output("full-event-load-status", "children", allow_duplicate=True),
                    "Loading full event. This can take a moment...",
                    "Full event load finished.",
                ),
                (
                    Output("full-event-load-status", "style", allow_duplicate=True),
                    {"color": "#fbbf24", "fontSize": "0.8em", "marginTop": "8px"},
                    {"color": "#888", "fontSize": "0.8em", "marginTop": "8px"},
                ),
            ],
        )
        def load_full_event(n_clicks, year, event):
            status_style = {"color": "#888", "fontSize": "0.8em", "marginTop": "8px"}
            if not n_clicks:
                return (
                    "Full event loads all available session overviews for this Grand Prix.",
                    status_style,
                )
            if not year or not event:
                return (
                    "Select a year and event before loading the full event.",
                    {**status_style, "color": "#fbbf24"},
                )

            try:
                result = session_service.cache_full_event(int(year), str(event))
            except Exception as e:
                return (
                    f"Could not load full event: {e}",
                    {**status_style, "color": "#ef4444"},
                )

            parts = []
            if result.loaded:
                parts.append(f"Loaded: {', '.join(result.loaded)}")
            if result.already_local:
                parts.append(f"Already local: {', '.join(result.already_local)}")
            if result.unavailable:
                parts.append(f"Unavailable: {', '.join(result.unavailable)}")

            if result.stopped_by_rate_limit:
                parts.append("Stopped because FastF1 rate limit was reached.")
                return " | ".join(parts), {**status_style, "color": "#ef4444"}

            if result.total_available:
                parts.append("Telemetry still loads per selected driver.")
                return " | ".join(parts), {**status_style, "color": "#4ade80"}

            return (
                "No sessions could be cached for this event.",
                {**status_style, "color": "#fbbf24"},
            )

        @app.callback(
            Output("bundle-store", "data"),
            Output("results-table", "columns"),
            Output("results-table", "data"),
            Output("results-table", "selected_rows"),
            Output("driver-dropdown", "options"),
            Output("driver-dropdown", "value"),
            Output("session-header", "children"),
            Output("session-load-status", "children"),
            Output("session-load-status", "style"),
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
            Output("tyre-strategy-graph", "figure"),
            Output("team-pace-graph", "figure"),
            Output("laptimes-dist-graph", "figure"),
            Input("load-button", "n_clicks"),
            State("year-input", "value"),
            State("event-input", "value"),
            State("session-input", "value"),
            State("user-store", "data"),
            prevent_initial_call=True,
            running=[
                (
                    Output("session-load-status", "children", allow_duplicate=True),
                    "Loading selected session...",
                    "Session load finished.",
                ),
                (
                    Output("session-load-status", "style", allow_duplicate=True),
                    {
                        "padding": "8px 12px", "marginBottom": "16px", "borderRadius": "6px",
                        "background": "#1a1a2e", "color": "#fbbf24", "border": "1px solid #333",
                        "display": "block",
                    },
                    {
                        "padding": "8px 12px", "marginBottom": "16px", "borderRadius": "6px",
                        "background": "#1a1a2e", "color": "#888", "border": "1px solid #333",
                        "display": "block",
                    },
                ),
            ],
        )
        def load_session(n_clicks, year, event, session_code, user_data):
            empty_pos = cls._empty_fig("Race Timeline – Position Chart")
            dash_empty = "—"
            base_status_style = {
                "padding": "8px 12px", "marginBottom": "16px", "borderRadius": "6px",
                "background": "#1a1a2e", "border": "1px solid #333", "display": "block",
            }
            try:
                result = session_service.load_session_overview(year, event, session_code)
                bundle = result.bundle
                cache_key = instance._store_session_bundle(year, event, session_code, bundle)
                results_table = get_results_table(bundle.results).reset_index(drop=True)

                # Get drivers from results/laps (no telemetry needed)
                drivers = []
                if not bundle.results.empty and "Driver" in bundle.results.columns:
                    drivers = sorted(bundle.results["Driver"].dropna().astype(str).unique().tolist())
                elif not bundle.laps.empty and "Driver" in bundle.laps.columns:
                    drivers = sorted(bundle.laps["Driver"].dropna().astype(str).unique().tolist())
                driver_repo.save_driver_codes(drivers)

                empty_tyre = cls._empty_fig("Tyre Strategy")
                empty_pace = cls._empty_fig("Team Pace Comparison")
                empty_dist = cls._empty_fig("Lap Times Distribution")

                if not drivers:
                    return ({}, [], [], [], [], None, "No driver data available.",
                            "Session loaded, but no drivers were found.",
                            {**base_status_style, "color": "#fbbf24"},
                            empty_pos, dash_empty, "", dash_empty, "", dash_empty, "", dash_empty, "", [],
                            empty_tyre, empty_pace, empty_dist)

                # Use favorite driver as default if available
                fav = (user_data or {}).get("favorite_driver")
                if fav and fav in drivers:
                    default_driver = fav
                else:
                    default_driver = cls._determine_default_driver(results_table, drivers)
                default_selected_rows = []
                if default_driver and not results_table.empty and "Driver" in results_table.columns:
                    matches = results_table.index[results_table["Driver"].astype(str) == str(default_driver)].tolist()
                    if matches:
                        default_selected_rows = [int(matches[0])]

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
                events_data = PitStopExtractor.extract(bundle.laps)
                driver_team = {}
                if not res.empty and "Driver" in res.columns:
                    team_col = "Team" if "Team" in res.columns else "TeamName" if "TeamName" in res.columns else None
                    if team_col:
                        driver_team.update(
                            {
                                str(row["Driver"]): str(row[team_col])
                                for _, row in res[["Driver", team_col]].dropna(subset=["Driver"]).iterrows()
                            }
                        )
                if not bundle.laps.empty and "Driver" in bundle.laps.columns and "Team" in bundle.laps.columns:
                    lap_teams = bundle.laps[["Driver", "Team"]].dropna(subset=["Driver"]).drop_duplicates("Driver")
                    driver_team.update(
                        {
                            str(row["Driver"]): str(row["Team"])
                            for _, row in lap_teams.iterrows()
                            if str(row["Driver"]) not in driver_team
                        }
                    )
                event_badges = []
                for ev in events_data:
                    badge_color = F1ColorPalette.get_team_color(driver_team.get(str(ev["driver"]), ""))
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
                    cls._to_datatable_columns(results_table),
                    results_table.to_dict("records"),
                    default_selected_rows,
                    cls._to_driver_dropdown_options(drivers),
                    default_driver,
                    f"{year} {event} – {session_code}",
                    result.message,
                    {
                        **base_status_style,
                        "color": "#4ade80" if result.source == "local" else "#fbbf24",
                    },
                    pos_fig,
                    p1_name, p1_team,
                    p2_name, p2_team,
                    p3_name, p3_team,
                    fl_name, fl_team,
                    event_badges,
                    TyreStrategyChart(bundle.laps).render() if not bundle.laps.empty else empty_tyre,
                    TeamPaceChart(bundle.laps).render() if not bundle.laps.empty else empty_pace,
                    LapTimesDistributionChart(bundle.laps).render() if not bundle.laps.empty else empty_dist,
                )
            except Exception as e:
                return ({}, [], [], [], [], None, f"Error loading session: {e}",
                        f"Could not load session: {e}",
                        {**base_status_style, "color": "#ef4444"},
                        empty_pos, dash_empty, "", dash_empty, "", dash_empty, "", dash_empty, "", [],
                        cls._empty_fig("Tyre Strategy"), cls._empty_fig("Team Pace"), cls._empty_fig("Lap Distribution"))

        @app.callback(
            Output("driver-dropdown", "value", allow_duplicate=True),
            Output("results-table", "selected_rows", allow_duplicate=True),
            Output("selected-drivers-status", "children"),
            Input("results-table", "selected_rows"),
            State("results-table", "data"),
            prevent_initial_call=True,
        )
        def select_driver_from_table(selected_rows, rows):
            if not selected_rows or not rows:
                return None, no_update, "Select up to 3 drivers in the finishing order table."
            limited_rows = [int(x) for x in selected_rows[:3]]
            drivers = cls._drivers_from_selected_rows(limited_rows, rows)
            if not drivers:
                return no_update, no_update, "Select up to 3 drivers in the finishing order table."
            limited_update = limited_rows if len(limited_rows) != len(selected_rows) else no_update
            suffix = " Only the first 3 selections are used." if len(selected_rows) > 3 else ""
            if len(drivers) == 1:
                message = f"Selected driver: {drivers[0]}. Use the lap controls for detailed telemetry."
            else:
                message = (
                    f"Selected drivers: {', '.join(drivers)}. "
                    "Telemetry plots compare each selected driver's fastest lap."
                )
            return drivers[0], limited_update, f"{message}{suffix}"

        @app.callback(
            Output("lap-table-title-1", "children"),
            Output("lap-selection-table-1", "columns"),
            Output("lap-selection-table-1", "data"),
            Output("lap-selection-table-1", "selected_rows"),
            Output("lap-table-panel-1", "style"),
            Output("lap-table-title-2", "children"),
            Output("lap-selection-table-2", "columns"),
            Output("lap-selection-table-2", "data"),
            Output("lap-selection-table-2", "selected_rows"),
            Output("lap-table-panel-2", "style"),
            Output("lap-table-title-3", "children"),
            Output("lap-selection-table-3", "columns"),
            Output("lap-selection-table-3", "data"),
            Output("lap-selection-table-3", "selected_rows"),
            Output("lap-table-panel-3", "style"),
            Output("lap-selection-status", "children"),
            Output("telemetry-load-status", "children"),
            Output("telemetry-load-status", "style"),
            Input("results-table", "selected_rows"),
            Input("results-table", "data"),
            Input("show-all-laps-toggle", "value"),
            State("bundle-store", "data"),
            running=[
                (
                    Output("telemetry-load-status", "children", allow_duplicate=True),
                    "Loading telemetry for selected drivers...",
                    "Telemetry selection update finished.",
                ),
                (
                    Output("telemetry-load-status", "style", allow_duplicate=True),
                    {"color": "#fbbf24", "fontSize": "0.8em", "marginBottom": "10px"},
                    {"color": "#888", "fontSize": "0.8em", "marginBottom": "10px"},
                ),
                (
                    Output("telemetry-loading-banner", "style", allow_duplicate=True),
                    {"display": "flex"},
                    {"display": "none"},
                ),
            ],
        )
        def update_lap_selection_table(selected_rows, rows, show_all_values, bundle_data):
            status_style = {"color": "#888", "fontSize": "0.8em", "marginBottom": "14px"}
            hidden_panel = {"display": "none"}
            show_all = "all" in (show_all_values or [])
            lap_limit = None if show_all else 10
            table_label = "all laps" if show_all else "10 fastest laps"
            drivers = cls._drivers_from_selected_rows(selected_rows, rows)
            if not drivers:
                outputs = []
                for _ in range(3):
                    outputs.extend(["", [], [], [], hidden_panel])
                return (*outputs, "Select drivers first.", "", status_style)
            bundle, telemetry_df = instance._retrieve_cached_bundle(bundle_data)
            if bundle is None:
                outputs = []
                for _ in range(3):
                    outputs.extend(["", [], [], [], hidden_panel])
                return (
                    *outputs,
                    "Load a session before selecting laps.",
                    "Load a session first.",
                    {**status_style, "color": "#fbbf24"},
                )

            bd = bundle_data or {}
            year, event, sc = bd.get("year"), bd.get("event"), bd.get("session")
            messages = []
            for driver in drivers:
                if telemetry_df.empty or driver not in telemetry_df["Driver"].astype(str).values:
                    try:
                        result = session_service.load_driver_telemetry(year, event, sc, driver)
                        bundle = result.bundle
                        instance._session_cache[bd.get("cache_key")] = bundle
                        telemetry_df = cls._clean_telemetry_dataframe(bundle.telemetry)
                        messages.append(result.message)
                    except Exception as e:
                        messages.append(f"Could not load {driver}: {e}")

            summary = cls._summary_for_drivers(telemetry_df, drivers)
            outputs = []
            for idx in range(3):
                if idx >= len(drivers):
                    outputs.extend(["", [], [], [], hidden_panel])
                    continue
                driver = drivers[idx]
                table = cls._top_lap_table_for_driver(summary, driver, limit=lap_limit)
                title = f"{driver}: {table_label}"
                selected = [0] if not table.empty else []
                panel_style = {"display": "block"}
                outputs.extend([title, cls._lap_table_columns(table), table.to_dict("records"), selected, panel_style])
            selection_text = (
                "Each driver table shows all laps. Scroll inside the table to browse them."
                if show_all
                else "Each driver table shows the 10 fastest laps."
            )
            selection_text += " The fastest lap is selected by default; select rows to choose exact laps for telemetry."
            telemetry_text = " | ".join(messages) if messages else "Telemetry ready from local cache."
            color = "#ef4444" if any("Could not" in msg for msg in messages) else "#4ade80"
            return (*outputs, selection_text, telemetry_text, {**status_style, "color": color})

        @app.callback(
            Output("track-lap-label-1", "children"),
            Output("track-lap-dropdown-1", "options"),
            Output("track-lap-dropdown-1", "value"),
            Output("track-lap-control-1", "style"),
            Output("track-lap-label-2", "children"),
            Output("track-lap-dropdown-2", "options"),
            Output("track-lap-dropdown-2", "value"),
            Output("track-lap-control-2", "style"),
            Output("track-lap-label-3", "children"),
            Output("track-lap-dropdown-3", "options"),
            Output("track-lap-dropdown-3", "value"),
            Output("track-lap-control-3", "style"),
            Input("results-table", "selected_rows"),
            Input("results-table", "data"),
            State("bundle-store", "data"),
        )
        def update_track_lap_controls(selected_rows, rows, bundle_data):
            drivers = cls._drivers_from_selected_rows(selected_rows, rows)
            bundle, telemetry_df = instance._retrieve_cached_bundle(bundle_data)
            outputs = []
            for idx in range(3):
                if idx >= len(drivers) or bundle is None:
                    outputs.extend(["", [], None, {"display": "none"}])
                    continue
                driver = drivers[idx]
                bd = bundle_data or {}
                year, event, sc = bd.get("year"), bd.get("event"), bd.get("session")
                if telemetry_df.empty or driver not in telemetry_df["Driver"].astype(str).values:
                    try:
                        result = session_service.load_driver_telemetry(year, event, sc, driver)
                        instance._session_cache[bd.get("cache_key")] = result.bundle
                        telemetry_df = cls._clean_telemetry_dataframe(result.bundle.telemetry)
                    except Exception:
                        outputs.extend([driver, [], None, {"display": "block"}])
                        continue
                laps = get_driver_laps(telemetry_df, driver)
                options = cls._to_lap_dropdown_options(laps)
                default = cls._select_default_laps(telemetry_df, driver, laps)
                outputs.extend([f"{driver} track lap", options, default[0] if default else None, {"display": "block"}])
            return tuple(outputs)

        @app.callback(
            Output("kpi-laps", "children"),
            Output("kpi-max-speed", "children"),
            Output("kpi-samples", "children"),
            Output("kpi-best-lap", "children"),
            Output("lap-summary-graph", "figure"),
            Output("speed-graph", "figure"),
            Output("gear-graph", "figure"),
            Output("inputs-graph", "figure"),
            Output("trackmap-graph", "figure"),
            Output("gear-map-graph", "figure"),
            Output("track-telemetry-store", "data"),
            Output("telemetry-loading-banner", "style", allow_duplicate=True),
            Input("driver-dropdown", "value"),
            Input("bundle-store", "data"),
            Input("results-table", "selected_rows"),
            Input("results-table", "data"),
            Input("lap-selection-table-1", "selected_rows"),
            Input("lap-selection-table-2", "selected_rows"),
            Input("lap-selection-table-3", "selected_rows"),
            Input("lap-selection-table-1", "data"),
            Input("lap-selection-table-2", "data"),
            Input("lap-selection-table-3", "data"),
            Input("track-lap-dropdown-1", "value"),
            Input("track-lap-dropdown-2", "value"),
            Input("track-lap-dropdown-3", "value"),
            Input("track-lap-dropdown-1", "options"),
            Input("track-lap-dropdown-2", "options"),
            Input("track-lap-dropdown-3", "options"),
            prevent_initial_call=True,
        )
        def update_dashboard(
            driver,
            bundle_data,
            selected_rows,
            rows,
            selected_lap_rows_1,
            selected_lap_rows_2,
            selected_lap_rows_3,
            lap_table_rows_1,
            lap_table_rows_2,
            lap_table_rows_3,
            track_lap_1,
            track_lap_2,
            track_lap_3,
            _track_lap_options_1,
            _track_lap_options_2,
            _track_lap_options_3,
        ):
            selected_drivers = cls._drivers_from_selected_rows(selected_rows, rows, fallback=driver)
            if not selected_drivers and driver:
                selected_drivers = [str(driver)]
            if not selected_drivers:
                return cls._empty_dashboard()

            bundle, telemetry_df = instance._retrieve_cached_bundle(bundle_data)
            if bundle is None:
                return cls._empty_dashboard()

            bd = bundle_data or {}
            year, event, sc = bd.get("year"), bd.get("event"), bd.get("session")
            for selected_driver in selected_drivers:
                if telemetry_df.empty or selected_driver not in telemetry_df["Driver"].astype(str).values:
                    if not year or not event or not sc:
                        continue
                    try:
                        result = session_service.load_driver_telemetry(year, event, sc, selected_driver)
                        bundle = result.bundle
                        instance._session_cache[bd.get("cache_key")] = bundle
                        telemetry_df = cls._clean_telemetry_dataframe(bundle.telemetry)
                    except Exception:
                        continue

            lap_frames = []
            for table_rows, selected_lap_rows in [
                (lap_table_rows_1, selected_lap_rows_1),
                (lap_table_rows_2, selected_lap_rows_2),
                (lap_table_rows_3, selected_lap_rows_3),
            ]:
                if not table_rows:
                    continue
                rows_to_use = selected_lap_rows if selected_lap_rows else [0]
                frame = cls._selected_lap_rows_to_df(table_rows, rows_to_use)
                if not frame.empty:
                    lap_frames.append(frame)
            lap_rows_df = pd.concat(lap_frames, ignore_index=True) if lap_frames else pd.DataFrame()
            if not lap_rows_df.empty and "Driver" in lap_rows_df.columns:
                lap_rows_df = lap_rows_df[lap_rows_df["Driver"].astype(str).isin(selected_drivers)].copy()
            if lap_rows_df.empty:
                summary_df = cls._summary_for_drivers(telemetry_df, selected_drivers)
                defaults = []
                for selected_driver in selected_drivers:
                    driver_table = cls._top_lap_table_for_driver(summary_df, selected_driver, limit=10)
                    if not driver_table.empty:
                        defaults.append(driver_table.iloc[[0]])
                lap_rows_df = pd.concat(defaults, ignore_index=True) if defaults else pd.DataFrame()

            lap_df = cls._telemetry_from_lap_rows(telemetry_df, lap_rows_df)
            selected_summary_df = cls._summary_from_telemetry(lap_df)
            all_summary_df = cls._summary_for_drivers(telemetry_df, selected_drivers)
            selected_count = len(selected_summary_df) if not selected_summary_df.empty else len(lap_rows_df)
            track_df = cls._track_telemetry_for_drivers(
                telemetry_df,
                selected_drivers,
                [track_lap_1, track_lap_2, track_lap_3],
            )

            if lap_df.empty:
                track_fig = cls._build_speed_track_grid(track_df)
                gear_track_fig = cls._build_gear_track_grid(track_df)
                return (
                    f"Selected Laps: {selected_count}",
                    "Max Speed: n/a", "Samples: 0", "Best Lap: n/a",
                    cls._empty_fig("Lap Times for Selected Drivers"),
                    cls._empty_fig("Speed"),
                    cls._empty_fig("Gear"),
                    cls._empty_fig("Throttle / Brake"),
                    track_fig,
                    gear_track_fig,
                    cls._track_store_data(track_df),
                    {"display": "none"},
                )

            kpis = cls._compute_kpi_strings(lap_df, selected_summary_df, selected_count)
            charts = cls._build_all_charts(
                lap_df,
                all_summary_df,
                selected_count,
                track_df,
            )

            return (
                *kpis,
                charts[0],
                *charts[1:],
                cls._track_store_data(track_df),
                {"display": "none"},
            )
