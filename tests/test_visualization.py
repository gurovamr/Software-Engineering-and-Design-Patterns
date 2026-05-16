"""Chart smoke tests for src.visualization."""

import pandas as pd
import plotly.graph_objects as go

from src.visualization import (
    DarkThemeConfig,
    F1ColorPalette,
    BaseChart,
    SpeedChart,
    LapSummaryChart,
    ThrottleBrakeChart,
    GearChart,
    TrackMapChart,
    PositionChart,
    TyreStrategyChart,
    TeamPaceChart,
    LapTimesDistributionChart,
    GearMapChart,
    DriverComparisonChart,
)


class TestDarkThemeConfig:
    def test_defaults(self):
        theme = DarkThemeConfig()
        assert theme.bg
        assert theme.grid
        assert theme.text


class TestF1ColorPalette:
    def test_team_and_compound_colors_return_strings(self):
        # use the exact method names from your code
        color_team = F1ColorPalette.get_team_color("Mercedes")
        color_compound = F1ColorPalette.get_compound_color("soft")
        assert isinstance(color_team, str)
        assert isinstance(color_compound, str)


class TestBaseChart:
    def test_empty_figure_has_title_and_height(self):
        # use the actual staticmethod name
        fig = BaseChart.empty_figure("Title", height=500)
        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Title"
        assert fig.layout.height == 500


class TestSpeedChart:
    def test_speed_chart_renders(self):
        df = pd.DataFrame(
            {"Distance": [0, 10], "Speed": [100, 150], "LapNumber": [1, 1]}
        )
        fig = SpeedChart(df).render()
        assert isinstance(fig, go.Figure)


class TestLapSummaryChart:
    def test_lap_summary_chart_renders(self):
        df = pd.DataFrame(
            {"LapNumber": [1, 2, 3], "LapTimeSeconds": [90.0, 89.5, 90.2]}
        )
        fig = LapSummaryChart(df).render()
        assert isinstance(fig, go.Figure)


class TestThrottleBrakeChart:
    def test_throttle_brake_chart_renders(self):
        df = pd.DataFrame(
            {
                "Distance": [0, 10],
                "Throttle": [0, 100],
                "Brake": [100, 0],
                "LapNumber": [1, 1],
            }
        )
        fig = ThrottleBrakeChart(df).render()
        assert isinstance(fig, go.Figure)


class TestGearChart:
    def test_gear_chart_renders(self):
        df = pd.DataFrame({"Distance": [0, 10], "nGear": [3, 5], "LapNumber": [1, 1]})
        fig = GearChart(df).render()
        assert isinstance(fig, go.Figure)


class TestTrackMapChart:
    def test_track_map_chart_renders(self):
        df = pd.DataFrame(
            {"X": [0.0, 1.0], "Y": [0.0, 1.0], "Speed": [100, 120], "LapNumber": [1, 1]}
        )
        fig = TrackMapChart(df).render()
        assert isinstance(fig, go.Figure)


class TestPositionChart:
    def test_position_chart_renders(self):
        df = pd.DataFrame(
            {
                "LapNumber": [1, 2, 3],
                "Position": [1, 2, 1],
                "Driver": ["VER", "VER", "VER"],
            }
        )
        fig = PositionChart(df).render()
        assert isinstance(fig, go.Figure)


class TestTyreStrategyChart:
    def test_tyre_strategy_chart_renders(self):
        df = pd.DataFrame(
            {
                "Driver": ["VER", "VER"],
                "Stint": [1, 2],
                "Compound": ["SOFT", "MEDIUM"],
                "LapNumber": [1, 10],
            }
        )
        fig = TyreStrategyChart(df).render()
        assert isinstance(fig, go.Figure)


class TestTeamPaceChart:
    def test_team_pace_chart_renders(self):
        df = pd.DataFrame(
            {"Team": ["Red Bull", "Red Bull"], "LapTimeSeconds": [89.5, 90.0]}
        )
        fig = TeamPaceChart(df).render()
        assert isinstance(fig, go.Figure)


class TestLapTimesDistributionChart:
    def test_lap_times_distribution_renders(self):
        df = pd.DataFrame(
            {"Driver": ["VER", "VER", "HAM"], "LapTimeSeconds": [89.5, 90.0, 90.2]}
        )
        # pass topn as positional to match __init__(df, topn)
        chart = LapTimesDistributionChart(df, 2)
        fig = chart.render()
        assert isinstance(fig, go.Figure)


class TestGearMapChart:
    def test_gear_map_chart_renders(self):
        df = pd.DataFrame({"X": [0, 1], "Y": [0, 1], "nGear": [3, 4]})
        fig = GearMapChart(df).render()
        assert isinstance(fig, go.Figure)


class TestDriverComparisonChart:
    def test_driver_comparison_chart_renders(self):
        tel1 = pd.DataFrame(
            {
                "Distance": [0, 10],
                "Speed": [100, 110],
                "Throttle": [0, 100],
                "Brake": [100, 0],
                "nGear": [3, 4],
                "Time": [0.0, 1.0],
            }
        )
        tel2 = pd.DataFrame(
            {
                "Distance": [0, 10],
                "Speed": [95, 105],
                "Throttle": [0, 90],
                "Brake": [100, 0],
                "nGear": [3, 4],
                "Time": [0.0, 1.1],
            }
        )
        fig = DriverComparisonChart(tel1, tel2, "VER", "HAM").render()
        assert isinstance(fig, go.Figure)
