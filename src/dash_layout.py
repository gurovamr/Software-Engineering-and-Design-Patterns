from dash import html, dcc, dash_table
import plotly.graph_objects as go


def empty_fig(title: str):
    fig = go.Figure()
    fig.update_layout(title=title, height=350)
    return fig


def create_layout():
    return html.Div(
        style={"display": "flex", "minHeight": "100vh"},
        children=[
            html.Div(
                style={
                    "width": "320px",
                    "padding": "20px",
                    "borderRight": "1px solid #ccc",
                },
                children=[
                    html.H2("F1 Telemetry"),

                    html.Label("Year"),
                    dcc.Input(id="year-input", type="number", value=2024, min=2018, max=2026),

                    html.Br(), html.Br(),
                    html.Label("Race / Event"),
                    dcc.Input(id="event-input", type="text", value="Monza"),

                    html.Br(), html.Br(),
                    html.Label("Session"),
                    dcc.Dropdown(
                        id="session-input",
                        options=[{"label": s, "value": s} for s in ["R", "Q", "FP1", "FP2", "FP3", "S", "SQ"]],
                        value="Q",
                        clearable=False,
                    ),

                    html.Br(),
                    html.Button("Load Session", id="load-button", n_clicks=0),

                    html.Hr(),

                    html.Label("Selected Driver"),
                    dcc.Dropdown(id="driver-dropdown", options=[], value=None, clearable=False),

                    html.Br(),
                    html.Label("Laps to compare"),
                    dcc.Dropdown(id="lap-dropdown", options=[], value=[], multi=True),

                    dcc.Store(id="bundle-store"),
                    dcc.Store(id="results-store"),
                ],
            ),

            html.Div(
                style={"flex": "1", "padding": "20px"},
                children=[
                    html.H1("Telemetry Dashboard"),
                    html.Div(id="session-header"),

                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr", "gap": "12px"},
                        children=[
                            html.Div(id="kpi-laps"),
                            html.Div(id="kpi-max-speed"),
                            html.Div(id="kpi-samples"),
                            html.Div(id="kpi-best-lap"),
                        ],
                    ),

                    html.H3("Driver Ranking / Classification"),
                    dash_table.DataTable(
                        id="results-table",
                        columns=[],
                        data=[],
                        row_selectable="single",
                        selected_rows=[],
                        style_table={"overflowX": "auto"},
                    ),

                    html.H3("Lap Comparison"),
                    dcc.Graph(id="lap-summary-graph", figure=empty_fig("Lap Comparison")),

                    html.H3("Lap Summary"),
                    dash_table.DataTable(
                        id="lap-summary-table",
                        columns=[],
                        data=[],
                        style_table={"overflowX": "auto"},
                    ),

                    html.H3("Telemetry Analysis"),
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
                        children=[
                            dcc.Graph(id="speed-graph", figure=empty_fig("Speed")),
                            dcc.Graph(id="gear-graph", figure=empty_fig("Gear")),
                        ],
                    ),
                    dcc.Graph(id="inputs-graph", figure=empty_fig("Throttle / Brake")),
                    dcc.Graph(id="trackmap-graph", figure=empty_fig("Track Map")),
                ],
            ),
        ],
    )