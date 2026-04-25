from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots



@dataclass(frozen=True)
class DarkThemeConfig:
    bg: str = "#1a1a2e"
    grid: str = "#333355"
    text: str = "#e0e0e0"



class F1ColorPalette:
    _TEAMS: dict[str, str] = {
        "Mercedes": "#27F4D2",
        "Red Bull Racing": "#3671C6",
        "Red Bull": "#3671C6",
        "Ferrari": "#E8002D",
        "McLaren": "#FF8000",
        "Aston Martin": "#229971",
        "Alpine": "#FF87BC",
        "Williams": "#64C4FF",
        "RB": "#6692FF",
        "AlphaTauri": "#6692FF",
        "Haas F1 Team": "#B6BABD",
        "Haas": "#B6BABD",
        "Kick Sauber": "#52E252",
        "Sauber": "#52E252",
        "Alfa Romeo": "#C92D4B",
        "Cadillac": "#FFD700",
    }

    _COMPOUNDS: dict[str, str] = {
        "SOFT": "#FF3333",
        "MEDIUM": "#FFC300",
        "HARD": "#EEEEEE",
        "INTERMEDIATE": "#39B54A",
        "WET": "#00BFFF",
        "UNKNOWN": "#888888",
        "TEST_UNKNOWN": "#888888",
    }

    _GEARS: list[str] = [
        "#882288",
        "#4444CC",
        "#22AACC",
        "#22CC66",
        "#AACC22",
        "#CCAA22",
        "#CC6622",
        "#CC2222",
    ]

    DRIVER_1 = "#4a90d9"
    DRIVER_2 = "#e04040"

    @classmethod
    def get_team_color(cls, team: str) -> str:
        if not team:
            return "#888888"
        for key, color in cls._TEAMS.items():
            if key.lower() in str(team).lower() or str(team).lower() in key.lower():
                return color
        return "#888888"

    @classmethod
    def get_compound_color(cls, name: str) -> str:
        return cls._COMPOUNDS.get(str(name).upper(), "#888888")

    @classmethod
    def get_gear_color(cls, n: int) -> str:
        if 1 <= n <= 8:
            return cls._GEARS[n - 1]
        return "#888888"

    @staticmethod
    def hex_to_rgba(hex_color: str, alpha: float = 0.2) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"



class BaseChart(ABC):
    _theme = DarkThemeConfig()

    def __init__(self, df: pd.DataFrame):
        self._df = df

    def render(self) -> go.Figure:
        fig = self._build()
        self._apply_theme(fig)
        return fig

    @abstractmethod
    def _build(self) -> go.Figure:
        ...

    def _apply_theme(self, fig: go.Figure) -> None:
        t = self._theme
        fig.update_layout(
            paper_bgcolor=t.bg,
            plot_bgcolor=t.bg,
            font=dict(color=t.text),
            margin=dict(l=40, r=20, t=50, b=40),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
            xaxis=dict(gridcolor=t.grid, zerolinecolor=t.grid),
            yaxis=dict(gridcolor=t.grid, zerolinecolor=t.grid),
        )

    @classmethod
    def empty_figure(cls, title: str = "", height: int = 400) -> go.Figure:
        fig = go.Figure()
        t = cls._theme
        fig.update_layout(
            title=dict(text=title, font=dict(color=t.text, size=14)),
            paper_bgcolor=t.bg,
            plot_bgcolor=t.bg,
            font=dict(color=t.text),
            height=height,
            margin=dict(l=40, r=20, t=50, b=40),
            xaxis=dict(gridcolor=t.grid, zerolinecolor=t.grid),
            yaxis=dict(gridcolor=t.grid, zerolinecolor=t.grid),
        )
        return fig



class SpeedChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = px.line(
            self._df, x="Distance", y="Speed", color="LapNumber",
            title="Speed over Distance",
            labels={"Distance": "Distance (m)", "Speed": "Speed (km/h)"},
        )
        fig.update_layout(height=350,
                          title=dict(font=dict(color=self._theme.text, size=14)))
        return fig


class LapSummaryChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = px.line(
            self._df, x="LapNumber", y="LapTimeSeconds", markers=True,
            title="Lap Time Comparison",
            labels={"LapNumber": "Lap", "LapTimeSeconds": "Lap Time (s)"},
        )
        fig.update_layout(height=350,
                          title=dict(font=dict(color=self._theme.text, size=14)))
        return fig


class ThrottleBrakeChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = go.Figure()
        for lap in sorted(self._df["LapNumber"].dropna().unique()):
            lap_df = self._df[self._df["LapNumber"] == lap]
            fig.add_trace(go.Scatter(
                x=lap_df["Distance"], y=lap_df["Throttle"],
                mode="lines", name=f"Throttle - Lap {int(lap)}",
            ))
            fig.add_trace(go.Scatter(
                x=lap_df["Distance"], y=lap_df["Brake"],
                mode="lines", name=f"Brake - Lap {int(lap)}",
                line=dict(dash="dot"),
            ))
        fig.update_layout(
            title="Throttle and Brake over Distance",
            xaxis_title="Distance (m)", yaxis_title="Input",
            height=350,
            title_font=dict(color=self._theme.text, size=14),
        )
        return fig


class GearChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = px.line(
            self._df, x="Distance", y="nGear", color="LapNumber",
            title="Gear over Distance",
            labels={"Distance": "Distance (m)", "nGear": "Gear"},
        )
        fig.update_layout(height=350,
                          title=dict(font=dict(color=self._theme.text, size=14)))
        return fig


class TrackMapChart(BaseChart):
    def _build(self) -> go.Figure:
        hover_cols = [c for c in ["LapNumber", "Distance", "Speed", "Throttle", "Brake", "nGear"]
                      if c in self._df.columns]
        fig = px.scatter(
            self._df, x="X", y="Y", color="Speed", symbol="LapNumber",
            hover_data=hover_cols, title="Track Map colored by Speed",
        )
        fig.update_traces(marker=dict(size=6))
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
        fig.update_layout(height=400,
                          title=dict(font=dict(color=self._theme.text, size=14)))
        return fig



class PositionChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = go.Figure()
        if self._df.empty or "Position" not in self._df.columns or "LapNumber" not in self._df.columns:
            fig.update_layout(height=400,
                              title=dict(text="Race Timeline – Position Chart",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        df = self._df[self._df["Position"].notna()].copy()
        if df.empty:
            fig.update_layout(height=400,
                              title=dict(text="Race Timeline – Position Chart",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        df["Position"] = df["Position"].astype(int)
        df["LapNumber"] = df["LapNumber"].astype(int)

        for driver in sorted(df["Driver"].unique()):
            d = df[df["Driver"] == driver].sort_values("LapNumber")
            team = d["Team"].iloc[0] if "Team" in d.columns and not d.empty else ""
            color = F1ColorPalette.get_team_color(team)

            pit_laps = d[d["PitInTime"].notna()] if "PitInTime" in d.columns else pd.DataFrame()

            fig.add_trace(go.Scatter(
                x=d["LapNumber"], y=d["Position"],
                mode="lines", name=driver,
                line=dict(color=color, width=2),
                hovertemplate=f"{driver}<br>Lap %{{x}}<br>P%{{y}}<extra></extra>",
            ))
            if not pit_laps.empty:
                fig.add_trace(go.Scatter(
                    x=pit_laps["LapNumber"], y=pit_laps["Position"],
                    mode="markers", name=f"{driver} pit",
                    marker=dict(color=color, size=8, symbol="diamond"),
                    showlegend=False,
                    hovertemplate=f"{driver} PIT<br>Lap %{{x}}<br>P%{{y}}<extra></extra>",
                ))

        fig.update_yaxes(autorange="reversed", dtick=1)
        fig.update_xaxes(title_text="Lap")
        fig.update_layout(showlegend=False, height=400,
                          title=dict(text="Race Timeline – Position Chart",
                                     font=dict(color=self._theme.text, size=14)))
        return fig


class TyreStrategyChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = go.Figure()
        if self._df.empty or "Stint" not in self._df.columns or "Compound" not in self._df.columns:
            fig.update_layout(height=500,
                              title=dict(text="Tyre Strategy",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        stints = (
            self._df[["Driver", "Stint", "Compound", "LapNumber"]]
            .groupby(["Driver", "Stint", "Compound"], sort=False)
            .count()
            .reset_index()
            .rename(columns={"LapNumber": "StintLength"})
        )

        if "Position" in self._df.columns:
            last_laps = self._df.sort_values("LapNumber").groupby("Driver").last()
            driver_order = last_laps.sort_values("Position").index.tolist()
        else:
            driver_order = sorted(stints["Driver"].unique())

        for driver in reversed(driver_order):
            driver_stints = stints[stints["Driver"] == driver].sort_values("Stint")
            prev_end = 0
            for _, row in driver_stints.iterrows():
                compound = str(row["Compound"]).upper()
                color = F1ColorPalette.get_compound_color(compound)
                length = int(row["StintLength"])
                fig.add_trace(go.Bar(
                    y=[driver], x=[length], base=prev_end, orientation="h",
                    marker=dict(color=color, line=dict(color="#222", width=0.5)),
                    name=compound, showlegend=False,
                    hovertemplate=f"{driver} — {compound}<br>{length} laps<extra></extra>",
                ))
                prev_end += length

        used = stints["Compound"].str.upper().unique()
        for compound in ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]:
            if compound in used:
                fig.add_trace(go.Bar(
                    y=[None], x=[0], marker=dict(color=F1ColorPalette.get_compound_color(compound)),
                    name=compound, showlegend=True,
                ))

        fig.update_layout(
            barmode="stack",
            yaxis=dict(categoryorder="array", categoryarray=list(reversed(driver_order))),
            xaxis_title="Lap",
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            height=max(400, len(driver_order) * 22 + 80),
            title=dict(text="Tyre Strategy",
                       font=dict(color=self._theme.text, size=14)),
        )
        return fig


class TeamPaceChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = go.Figure()
        if self._df.empty or "LapTime" not in self._df.columns or "Team" not in self._df.columns:
            fig.update_layout(height=400,
                              title=dict(text="Team Pace Comparison",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        df = self._df.copy()
        df["LapTimeSec"] = df["LapTime"].dt.total_seconds()
        df = df[df["LapTimeSec"].notna()]

        fastest = df["LapTimeSec"].min()
        df = df[df["LapTimeSec"] <= fastest * 1.07]
        if df.empty:
            fig.update_layout(height=400,
                              title=dict(text="Team Pace Comparison",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        team_median = df.groupby("Team")["LapTimeSec"].median().sort_values()
        for team in team_median.index:
            color = F1ColorPalette.get_team_color(team)
            fig.add_trace(go.Box(
                y=df[df["Team"] == team]["LapTimeSec"], name=team,
                marker=dict(color=color, size=4), line=dict(color=color),
            ))

        fig.update_layout(
            showlegend=False, yaxis_title="Lap Time (s)",
            xaxis=dict(tickangle=-45), height=450,
            title=dict(text="Team Pace Comparison",
                       font=dict(color=self._theme.text, size=14)),
        )
        return fig


class LapTimesDistributionChart(BaseChart):
    def __init__(self, df: pd.DataFrame, top_n: int = 10):
        super().__init__(df)
        self._top_n = top_n

    def _build(self) -> go.Figure:
        fig = go.Figure()
        if self._df.empty or "LapTime" not in self._df.columns or "Driver" not in self._df.columns:
            fig.update_layout(height=400,
                              title=dict(text="Lap Times Distribution",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        df = self._df.copy()
        df["LapTimeSec"] = df["LapTime"].dt.total_seconds()
        df = df[df["LapTimeSec"].notna()]

        fastest = df["LapTimeSec"].min()
        df = df[df["LapTimeSec"] <= fastest * 1.07]
        if df.empty:
            fig.update_layout(height=400,
                              title=dict(text="Lap Times Distribution",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        if "Position" in df.columns:
            last_laps = df.sort_values("LapNumber").groupby("Driver").last()
            driver_order = last_laps.sort_values("Position").index.tolist()[:self._top_n]
        else:
            driver_order = sorted(df["Driver"].unique())[:self._top_n]

        df = df[df["Driver"].isin(driver_order)]

        for driver in driver_order:
            d = df[df["Driver"] == driver]
            team = d["Team"].iloc[0] if "Team" in d.columns and not d.empty else ""
            color = F1ColorPalette.get_team_color(team)
            fill = F1ColorPalette.hex_to_rgba(color, 0.2)

            fig.add_trace(go.Violin(
                y=d["LapTimeSec"], name=driver,
                box_visible=True, meanline_visible=True,
                line_color=color, fillcolor=fill,
                points="all", pointpos=0, jitter=0.3,
                marker=dict(size=3, color=color),
            ))

        fig.update_layout(
            showlegend=False, yaxis_title="Lap Time (s)",
            violinmode="group", height=450,
            title=dict(text="Lap Times Distribution",
                       font=dict(color=self._theme.text, size=14)),
        )
        return fig


class GearMapChart(BaseChart):
    def _build(self) -> go.Figure:
        fig = go.Figure()
        if self._df.empty:
            fig.update_layout(height=450,
                              title=dict(text="Gear Shifts on Track",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        needed = {"X", "Y", "nGear"}
        if not needed.issubset(self._df.columns):
            fig.update_layout(height=450,
                              title=dict(text="Gear Shifts on Track",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        df = self._df.copy()
        df["nGear"] = pd.to_numeric(df["nGear"], errors="coerce")
        df = df[df["nGear"].notna()]
        if df.empty:
            fig.update_layout(height=450,
                              title=dict(text="Gear Shifts on Track",
                                         font=dict(color=self._theme.text, size=14)))
            return fig

        for gear in sorted(df["nGear"].unique()):
            gear_int = int(gear)
            color = F1ColorPalette.get_gear_color(gear_int)
            gd = df[df["nGear"] == gear]
            fig.add_trace(go.Scatter(
                x=gd["X"], y=gd["Y"], mode="markers",
                marker=dict(color=color, size=4),
                name=f"Gear {gear_int}",
                hovertemplate=f"Gear {gear_int}<extra></extra>",
            ))

        fig.update_yaxes(scaleanchor="x", scaleratio=1)
        fig.update_layout(
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
            height=450,
            title=dict(text="Gear Shifts on Track",
                       font=dict(color=self._theme.text, size=14)),
        )
        return fig



class TwoDriverChart(ABC):
    """
    Abstract base for charts that compare exactly two drivers.

    Satisfies LSP: subclasses share the same two-DataFrame constructor
    contract instead of breaking BaseChart's single-DataFrame interface.

    Pattern: Template Method
    """

    _theme = DarkThemeConfig()

    def __init__(
        self,
        tel1: pd.DataFrame,
        tel2: pd.DataFrame,
        driver1: str,
        driver2: str,
    ) -> None:
        self._tel1 = tel1
        self._tel2 = tel2
        self._driver1 = driver1
        self._driver2 = driver2

    def render(self) -> go.Figure:
        fig = self._build()
        self._apply_theme(fig)
        return fig

    @abstractmethod
    def _build(self) -> go.Figure: ...

    def _apply_theme(self, fig: go.Figure) -> None:
        t = self._theme
        fig.update_layout(
            paper_bgcolor=t.bg,
            plot_bgcolor=t.bg,
            font=dict(color=t.text, size=11),
        )
        for i in range(1, 6):
            fig.update_xaxes(gridcolor=t.grid, zerolinecolor=t.grid, row=i, col=1)
            fig.update_yaxes(gridcolor=t.grid, zerolinecolor=t.grid, row=i, col=1)
        for ann in fig.layout.annotations:
            ann.font.color = t.text
            ann.font.size = 11


class DriverComparisonChart(TwoDriverChart):
    def __init__(
        self,
        tel1: pd.DataFrame,
        tel2: pd.DataFrame,
        d1: str,
        d2: str,
        title: str = "",
        lap_time1: str = "",
        lap_time2: str = "",
    ):
        super().__init__(tel1, tel2, d1, d2)
        self._title = title
        self._lap_time1 = lap_time1
        self._lap_time2 = lap_time2

    def _build(self) -> go.Figure:
        row_titles = [
            "Speed (km/h)", "Throttle (%)", "Brake",
            "Gear", f"Δ {self._driver1}–{self._driver2} (s)",
        ]
        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.25, 0.2, 0.15, 0.2, 0.2],
            subplot_titles=row_titles,
        )

        c1, c2 = F1ColorPalette.DRIVER_1, F1ColorPalette.DRIVER_2
        tel1, tel2 = self._tel1, self._tel2

        def _add(df, y_col, row, name, color, showlegend=False):
            if y_col not in df.columns or "Distance" not in df.columns:
                return
            fig.add_trace(go.Scatter(
                x=df["Distance"], y=df[y_col],
                mode="lines", name=name,
                line=dict(color=color, width=1.5),
                showlegend=showlegend,
            ), row=row, col=1)

        _add(tel1, "Speed", 1, self._driver1, c1, showlegend=True)
        _add(tel2, "Speed", 1, self._driver2, c2, showlegend=True)
        _add(tel1, "Throttle", 2, self._driver1, c1)
        _add(tel2, "Throttle", 2, self._driver2, c2)
        _add(tel1, "Brake", 3, self._driver1, c1)
        _add(tel2, "Brake", 3, self._driver2, c2)
        _add(tel1, "nGear", 4, self._driver1, c1)
        _add(tel2, "nGear", 4, self._driver2, c2)

        ref_dist, delta = self._compute_delta(tel1, tel2)
        if len(ref_dist) > 0:
            fig.add_trace(go.Scatter(
                x=ref_dist, y=delta, mode="lines", name="Δ",
                line=dict(color="#aaa", width=1),
                fill="tozeroy", fillcolor="rgba(180,180,180,0.25)",
                showlegend=False,
            ), row=5, col=1)
            fig.add_hline(y=0, line=dict(color="#555", dash="dash", width=0.8), row=5, col=1)

        subtitle = self._build_delta_subtitle(ref_dist, delta)
        fig.update_layout(
            title=dict(
                text=(f"{self._title}<br><span style='font-size:11px;color:#aaa'>"
                      f"{subtitle}</span>" if subtitle else self._title),
                font=dict(color=self._theme.text, size=15),
            ),
            height=750,
            margin=dict(l=50, r=20, t=70, b=40),
            legend=dict(
                bgcolor="rgba(0,0,0,0)", font=dict(size=11),
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            ),
            hovermode="x unified",
        )

        fig.update_xaxes(title_text="Distance (m)", row=5, col=1)
        return fig

    @staticmethod
    def _compute_delta(tel1: pd.DataFrame, tel2: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if "Time" not in tel1.columns or "Time" not in tel2.columns:
            return np.array([]), np.array([])
        if "Distance" not in tel1.columns or "Distance" not in tel2.columns:
            return np.array([]), np.array([])

        t1 = tel1.sort_values("Distance").copy()
        t2 = tel2.sort_values("Distance").copy()

        def _time_to_seconds(series: pd.Series) -> np.ndarray:
            if series.empty or series.isna().all():
                return np.array([], dtype=float)
            if pd.api.types.is_timedelta64_dtype(series):
                return series.dt.total_seconds().to_numpy()
            return pd.to_numeric(series, errors="coerce").to_numpy()
        t1_sec = _time_to_seconds(t1["Time"])
        t2_sec = _time_to_seconds(t2["Time"])
        if len(t1_sec) == 0 or len(t2_sec) == 0:
            return np.array([]), np.array([])

        dist_min = max(t1["Distance"].min(), t2["Distance"].min())
        dist_max = min(t1["Distance"].max(), t2["Distance"].max())
        if dist_min >= dist_max:
            return np.array([]), np.array([])
        ref_dist = np.linspace(dist_min, dist_max, min(500, len(t1)))

        time1_interp = np.interp(ref_dist, t1["Distance"].values, t1_sec)
        time2_interp = np.interp(ref_dist, t2["Distance"].values, t2_sec)

        return ref_dist, time1_interp - time2_interp

    def _build_delta_subtitle(self, ref_dist: np.ndarray, delta: np.ndarray) -> str:
        parts: list[str] = []
        if self._lap_time1:
            parts.append(f"{self._driver1}: {self._lap_time1}")
        if self._lap_time2:
            parts.append(f"{self._driver2}: {self._lap_time2}")
        if len(ref_dist) > 0:
            final = delta[-1]
            faster = self._driver1 if final < 0 else self._driver2
            parts.append(f"Δ {abs(final):.3f}s ({faster} faster)")
        return " | ".join(parts)
