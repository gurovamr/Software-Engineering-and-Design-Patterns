from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_speed(df: pd.DataFrame):
    fig = px.line(
        df,
        x="Distance",
        y="Speed",
        color="LapNumber",
        title="Speed over Distance",
        labels={"Distance": "Distance (m)", "Speed": "Speed (km/h)"}
    )
    return fig

def plot_lap_summary(summary_df: pd.DataFrame):
    fig = px.line(
        summary_df,
        x="LapNumber",
        y="LapTimeSeconds",
        markers=True,
        title="Lap Time Comparison",
        labels={"LapNumber": "Lap", "LapTimeSeconds": "Lap Time (s)"}
    )
    return fig

def plot_throttle_brake(df: pd.DataFrame):
    fig = go.Figure()

    for lap in sorted(df["LapNumber"].dropna().unique()):
        lap_df = df[df["LapNumber"] == lap]

        fig.add_trace(go.Scatter(
            x=lap_df["Distance"],
            y=lap_df["Throttle"],
            mode="lines",
            name=f"Throttle - Lap {int(lap)}"
        ))
        fig.add_trace(go.Scatter(
            x=lap_df["Distance"],
            y=lap_df["Brake"],
            mode="lines",
            name=f"Brake - Lap {int(lap)}",
            line=dict(dash="dot")
        ))

    fig.update_layout(
        title="Throttle and Brake over Distance",
        xaxis_title="Distance (m)",
        yaxis_title="Input"
    )
    return fig


def plot_gear(df: pd.DataFrame):
    fig = px.line(
        df,
        x="Distance",
        y="nGear",
        color="LapNumber",
        title="Gear over Distance",
        labels={"Distance": "Distance (m)", "nGear": "Gear"}
    )
    return fig


def plot_track_map(df: pd.DataFrame):
    hover_cols = [c for c in ["LapNumber", "Distance", "Speed", "Throttle", "Brake", "nGear"] if c in df.columns]

    fig = px.scatter(
        df,
        x="X",
        y="Y",
        color="Speed",
        symbol="LapNumber",
        hover_data=hover_cols,
        title="Track Map colored by Speed"
    )

    fig.update_traces(marker=dict(size=6))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig

