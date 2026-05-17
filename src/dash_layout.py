from datetime import date

from dash import dcc, dash_table, html
import plotly.graph_objects as go

_current_year = date.today().year

_BG = "#0d0d1a"
_CARD_BG = "#1a1a2e"
_ACCENT = "#e10600"
_TEXT = "#e0e0e0"
_MUTED = "#888"
_BORDER = "#333"


def empty_fig(title: str):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=350,
        paper_bgcolor=_CARD_BG,
        plot_bgcolor=_CARD_BG,
        font=dict(color=_TEXT),
    )
    return fig


_CARD_STYLE = {
    "background": _CARD_BG,
    "borderRadius": "10px",
    "padding": "16px",
    "border": f"1px solid {_BORDER}",
}

_LABEL_STYLE = {"color": _MUTED, "fontSize": "0.85em", "marginBottom": "4px"}

_KPI_STYLE = {
    **_CARD_STYLE,
    "textAlign": "center",
    "padding": "12px",
}


def _section_title(text: str, margin_top: str = "4px"):
    return html.Div(
        text,
        style={
            "fontSize": "1.15em",
            "fontWeight": "bold",
            "color": _TEXT,
            "margin": f"{margin_top} 0 12px",
        },
    )


def _login_page():
    return html.Div(
        id="login-page",
        style={
            "maxWidth": "400px",
            "margin": "120px auto",
            "padding": "30px",
            "background": _CARD_BG,
            "borderRadius": "12px",
            "border": f"1px solid {_BORDER}",
            "color": _TEXT,
        },
        children=[
            html.H2("F1 Telemetry - Login", style={"color": _ACCENT}),
            html.Label("Username", style={"color": _TEXT}),
            dcc.Input(
                id="login-name",
                type="text",
                placeholder="Enter username",
                style={
                    "width": "100%",
                    "marginBottom": "12px",
                    "background": _BG,
                    "color": _TEXT,
                    "border": f"1px solid {_BORDER}",
                },
            ),
            html.Label("Password", style={"color": _TEXT}),
            dcc.Input(
                id="login-password",
                type="password",
                placeholder="Enter password",
                style={
                    "width": "100%",
                    "marginBottom": "12px",
                    "background": _BG,
                    "color": _TEXT,
                    "border": f"1px solid {_BORDER}",
                },
            ),
            html.Label("Favorite Driver (optional)", style={"color": _TEXT}),
            dcc.Interval(id="driver-options-loader", interval=500, max_intervals=1),
            dcc.Loading(
                type="circle",
                children=dcc.Dropdown(
                    id="login-fav-driver",
                    options=[],
                    value=None,
                    disabled=True,
                    placeholder="Loading drivers...",
                    style={"marginBottom": "6px"},
                ),
            ),
            html.Div(
                id="driver-options-status",
                children="Loading driver list...",
                style={"color": _MUTED, "fontSize": "0.8em", "marginBottom": "16px"},
            ),
            html.Div(
                style={"display": "flex", "gap": "10px"},
                children=[
                    html.Button(
                        "Login",
                        id="btn-login",
                        n_clicks=0,
                        style={
                            "background": _ACCENT,
                            "color": "white",
                            "border": "none",
                            "padding": "8px 20px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                        },
                    ),
                    html.Button(
                        "Register",
                        id="btn-register",
                        n_clicks=0,
                        style={
                            "background": _BORDER,
                            "color": _TEXT,
                            "border": "none",
                            "padding": "8px 20px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                        },
                    ),
                ],
            ),
            html.Div(id="login-message", style={"color": "#ff6b6b", "marginTop": "10px"}),
        ],
    )


def _podium_card(card_id, rank_label, rank_color):
    return html.Div(
        id=card_id,
        style={
            **_CARD_STYLE,
            "textAlign": "center",
            "minWidth": "160px",
            "flex": "1",
        },
        children=[
            html.Div(
                rank_label,
                style={
                    "fontSize": "0.75em",
                    "fontWeight": "bold",
                    "color": rank_color,
                    "textTransform": "uppercase",
                    "marginBottom": "6px",
                },
            ),
            html.Div(
                "-",
                id=f"{card_id}-name",
                style={"fontSize": "1.1em", "fontWeight": "bold", "color": _TEXT},
            ),
            html.Div("", id=f"{card_id}-team", style={"fontSize": "0.8em", "color": _MUTED}),
        ],
    )


def _sidebar():
    return html.Div(
        style={
            "width": "280px",
            "padding": "20px",
            "background": _CARD_BG,
            "borderRight": f"1px solid {_BORDER}",
            "flexShrink": "0",
        },
        children=[
            html.Label("Year", style=_LABEL_STYLE),
            dcc.Dropdown(
                id="year-input",
                options=[{"label": str(y), "value": y} for y in range(_current_year, 2017, -1)],
                value=_current_year,
                clearable=False,
                style={"marginBottom": "12px"},
            ),
            html.Label("Race / Event", style=_LABEL_STYLE),
            dcc.Dropdown(
                id="event-input",
                options=[],
                value=None,
                placeholder="Select event...",
                style={"marginBottom": "12px"},
            ),
            html.Label("Session", style=_LABEL_STYLE),
            dcc.Dropdown(
                id="session-input",
                options=[{"label": s, "value": s} for s in ["R", "Q", "FP1", "FP2", "FP3", "S", "SQ"]],
                value="R",
                clearable=False,
                style={"marginBottom": "16px"},
            ),
            dcc.Loading(
                id="loading-session",
                type="circle",
                children=html.Button(
                    "Load Session",
                    id="load-button",
                    n_clicks=0,
                    style={
                        "width": "100%",
                        "background": _ACCENT,
                        "color": "white",
                        "border": "none",
                        "padding": "10px",
                        "borderRadius": "6px",
                        "cursor": "pointer",
                        "fontWeight": "bold",
                    },
                ),
            ),
            dcc.Loading(
                id="loading-full-event",
                type="circle",
                children=html.Button(
                    "Load Full Event",
                    id="load-full-event-button",
                    n_clicks=0,
                    style={
                        "width": "100%",
                        "background": _BORDER,
                        "color": _TEXT,
                        "border": "none",
                        "padding": "9px",
                        "borderRadius": "6px",
                        "cursor": "pointer",
                        "fontWeight": "bold",
                        "marginTop": "8px",
                    },
                ),
            ),
            html.Div(
                id="full-event-load-status",
                children="Full event loads all available session overviews for this Grand Prix.",
                style={"color": _MUTED, "fontSize": "0.8em", "marginTop": "8px"},
            ),
            html.Div(
                style={"display": "none"},
                children=dcc.Dropdown(id="driver-dropdown", options=[], value=None, clearable=False),
            ),
            dcc.Store(id="bundle-store"),
            dcc.Store(id="results-store"),
            dcc.Store(id="track-telemetry-store"),
            dcc.Store(id="track-hover-sync-store"),
        ],
    )


def _results_table():
    return html.Div(
        style={**_CARD_STYLE, "marginBottom": "20px", "padding": "0", "overflow": "hidden"},
        children=[
            html.Div(
                "Finishing Order: Select up to 3 drivers for analysis",
                style={
                    "padding": "12px 16px",
                    "fontWeight": "bold",
                    "fontSize": "1em",
                    "borderBottom": f"1px solid {_BORDER}",
                },
            ),
            dash_table.DataTable(
                id="results-table",
                columns=[],
                data=[],
                row_selectable="multi",
                selected_rows=[],
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": _CARD_BG,
                    "color": _TEXT,
                    "fontWeight": "bold",
                    "border": f"1px solid {_BORDER}",
                },
                style_cell={
                    "backgroundColor": _BG,
                    "color": _TEXT,
                    "border": f"1px solid {_BORDER}",
                    "padding": "8px 12px",
                    "fontSize": "0.9em",
                    "textAlign": "left",
                },
                style_data_conditional=[
                    {"if": {"state": "active"}, "backgroundColor": "#2a2a4e", "border": f"1px solid {_ACCENT}"},
                    {"if": {"state": "selected"}, "backgroundColor": "#2a2a4e", "border": f"1px solid {_ACCENT}"},
                ],
            ),
        ],
    )


def _lap_table_panel(index):
    return html.Div(
        id=f"lap-table-panel-{index}",
        style={"display": "none"},
        children=[
            html.Div(
                id=f"lap-table-title-{index}",
                style={"fontWeight": "bold", "marginBottom": "8px", "color": _TEXT},
            ),
            dash_table.DataTable(
                id=f"lap-selection-table-{index}",
                columns=[],
                data=[],
                row_selectable="multi",
                selected_rows=[],
                page_action="none",
                fixed_rows={"headers": True},
                style_table={"height": "310px", "overflowY": "auto", "overflowX": "auto"},
                style_header={
                    "backgroundColor": _CARD_BG,
                    "color": _TEXT,
                    "fontWeight": "bold",
                    "border": f"1px solid {_BORDER}",
                },
                style_cell={
                    "backgroundColor": _BG,
                    "color": _TEXT,
                    "border": f"1px solid {_BORDER}",
                    "padding": "6px 10px",
                    "fontSize": "0.85em",
                    "textAlign": "left",
                },
                style_data_conditional=[
                    {"if": {"state": "selected"}, "backgroundColor": "#2a2a4e", "border": f"1px solid {_ACCENT}"},
                ],
            ),
        ],
    )


def _dashboard_page():
    return html.Div(
        id="dashboard-page",
        style={"display": "none", "background": _BG, "color": _TEXT, "minHeight": "100vh"},
        children=[
            html.Div(id="sync-status", style={"padding": "6px 16px", "textAlign": "center", "fontSize": "0.85em"}),
            dcc.Interval(id="sync-interval", interval=2000, disabled=True),
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "padding": "10px 24px",
                    "borderBottom": f"1px solid {_BORDER}",
                },
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                        children=[
                            html.Span("F1", style={"fontSize": "1.1em", "fontWeight": "bold", "color": _ACCENT}),
                            html.Span("F1 Telemetry", style={"fontSize": "1.2em", "fontWeight": "bold", "color": _TEXT}),
                        ],
                    ),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                        children=[
                            html.Span(id="user-greeting", style={"fontSize": "0.85em", "color": _MUTED}),
                            html.Button(
                                "Logout",
                                id="btn-logout",
                                n_clicks=0,
                                style={
                                    "background": _BORDER,
                                    "color": _TEXT,
                                    "border": "none",
                                    "padding": "4px 14px",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                    "fontSize": "0.8em",
                                },
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"display": "flex", "minHeight": "calc(100vh - 60px)"},
                children=[
                    _sidebar(),
                    html.Div(
                        style={"flex": "1", "padding": "20px", "overflowY": "auto"},
                        children=[
                            html.Div(
                                id="session-header",
                                style={
                                    "fontSize": "1.4em",
                                    "fontWeight": "bold",
                                    "color": _TEXT,
                                    "marginBottom": "16px",
                                },
                            ),
                            html.Div(
                                id="session-load-status",
                                style={
                                    "padding": "8px 12px",
                                    "marginBottom": "16px",
                                    "borderRadius": "6px",
                                    "background": _CARD_BG,
                                    "color": _MUTED,
                                    "border": f"1px solid {_BORDER}",
                                    "display": "none",
                                },
                            ),

                            _section_title("Race Overview"),
                            html.Div(
                                style={"display": "flex", "gap": "12px", "marginBottom": "20px", "flexWrap": "wrap"},
                                children=[
                                    _podium_card("podium-p1", "P1 - Winner", "#FFD700"),
                                    _podium_card("podium-p2", "P2", "#C0C0C0"),
                                    _podium_card("podium-p3", "P3", "#CD7F32"),
                                    _podium_card("podium-fastest", "Fastest Lap", "#a855f7"),
                                ],
                            ),
                            html.Div(
                                className="kpi-grid",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(4, minmax(120px, 1fr))",
                                    "gap": "10px",
                                    "marginBottom": "20px",
                                },
                                children=[
                                    html.Div(id="kpi-laps", style=_KPI_STYLE),
                                    html.Div(id="kpi-max-speed", style=_KPI_STYLE),
                                    html.Div(id="kpi-samples", style=_KPI_STYLE),
                                    html.Div(id="kpi-best-lap", style=_KPI_STYLE),
                                ],
                            ),
                            html.Div(
                                className="race-overview-grid",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "minmax(0, 1.35fr) minmax(280px, 0.65fr)",
                                    "gap": "16px",
                                    "marginBottom": "20px",
                                },
                                children=[
                                    html.Div(
                                        style={**_CARD_STYLE, "padding": "0", "overflow": "hidden"},
                                        children=[
                                            dcc.Graph(
                                                id="position-chart-graph",
                                                figure=empty_fig("Race Timeline - Position Chart"),
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        style={**_CARD_STYLE},
                                        children=[
                                            html.Div(
                                                "Key Events",
                                                style={"fontWeight": "bold", "marginBottom": "10px", "fontSize": "1em"},
                                            ),
                                            html.Div(
                                                id="key-events-container",
                                                style={"display": "flex", "flexWrap": "wrap", "gap": "8px"},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dcc.Graph(id="tyre-strategy-graph", figure=empty_fig("Tyre Strategy"), style={"marginBottom": "20px"}),
                            html.Div(
                                className="race-chart-grid",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "16px",
                                    "marginBottom": "20px",
                                },
                                children=[
                                    dcc.Graph(id="team-pace-graph", figure=empty_fig("Team Pace Comparison")),
                                    dcc.Graph(id="laptimes-dist-graph", figure=empty_fig("Lap Times Distribution")),
                                ],
                            ),

                            _section_title("Driver Analysis", margin_top="10px"),
                            _results_table(),
                            html.Div(
                                id="selected-drivers-status",
                                style={"color": _MUTED, "fontSize": "0.85em", "margin": "-10px 0 14px"},
                            ),
                            html.Div(
                                id="driver-analysis-card",
                                style={**_CARD_STYLE, "marginBottom": "20px"},
                                children=[
                                    html.Div(
                                        id="telemetry-loading-banner",
                                        className="telemetry-loading-banner",
                                        style={"display": "none"},
                                        children=[
                                            html.Span(className="telemetry-spinner"),
                                            html.Span("Loading telemetry for selected drivers..."),
                                        ],
                                    ),
                                    html.Div(
                                        style={
                                            "display": "flex",
                                            "alignItems": "center",
                                            "justifyContent": "space-between",
                                            "gap": "12px",
                                            "marginBottom": "8px",
                                            "flexWrap": "wrap",
                                        },
                                        children=[
                                            html.Div("Lap Times for Selected Drivers", style={"fontWeight": "bold"}),
                                        ],
                                    ),
                                    dcc.Graph(
                                        id="lap-summary-graph",
                                        figure=empty_fig("Lap Times for Selected Drivers"),
                                        style={"marginBottom": "0"},
                                    ),
                                    html.Div(
                                        className="lap-table-controls",
                                        children=[
                                            html.Div(
                                                id="lap-selection-status",
                                                className="lap-selection-status",
                                                style={"color": _TEXT, "fontSize": "0.85em", "marginBottom": "6px"},
                                            ),
                                            dcc.Checklist(
                                                id="show-all-laps-toggle",
                                                options=[{"label": "Show all laps", "value": "all"}],
                                                value=[],
                                                className="show-all-laps-toggle",
                                                labelStyle={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "gap": "6px",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="lap-table-grid",
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "repeat(3, minmax(220px, 1fr))",
                                            "gap": "14px",
                                        },
                                        children=[
                                            _lap_table_panel(1),
                                            _lap_table_panel(2),
                                            _lap_table_panel(3),
                                        ],
                                    ),
                                    html.Div(
                                        id="telemetry-load-status",
                                        style={"color": _MUTED, "fontSize": "0.8em", "marginBottom": "10px"},
                                    ),
                                ],
                            ),
                            html.Div(
                                className="telemetry-grid",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "16px",
                                    "marginBottom": "20px",
                                },
                                children=[
                                    dcc.Loading(
                                        id="loading-speed-graph",
                                        type="circle",
                                        children=dcc.Graph(id="speed-graph", figure=empty_fig("Speed")),
                                    ),
                                    dcc.Loading(
                                        id="loading-gear-graph",
                                        type="circle",
                                        children=dcc.Graph(id="gear-graph", figure=empty_fig("Gear")),
                                    ),
                                ],
                            ),
                            dcc.Loading(
                                id="loading-inputs-graph",
                                type="circle",
                                children=dcc.Graph(
                                    id="inputs-graph",
                                    figure=empty_fig("Throttle / Brake"),
                                    style={"marginBottom": "20px"},
                                ),
                            ),
                            html.Div(
                                style={**_CARD_STYLE, "marginBottom": "20px"},
                                children=[
                                    html.Div("Track Map Laps", style={"fontWeight": "bold", "marginBottom": "10px"}),
                                    dcc.Loading(
                                        id="loading-track-lap-controls",
                                        type="circle",
                                        children=html.Div(
                                            className="track-map-controls-grid",
                                            style={
                                                "display": "grid",
                                                "gridTemplateColumns": "repeat(3, minmax(180px, 1fr))",
                                                "gap": "12px",
                                            },
                                            children=[
                                                html.Div(id="track-lap-control-1", children=[
                                                    html.Label(id="track-lap-label-1", style=_LABEL_STYLE),
                                                    dcc.Dropdown(id="track-lap-dropdown-1", options=[], value=None, clearable=False),
                                                ]),
                                                html.Div(id="track-lap-control-2", children=[
                                                    html.Label(id="track-lap-label-2", style=_LABEL_STYLE),
                                                    dcc.Dropdown(id="track-lap-dropdown-2", options=[], value=None, clearable=False),
                                                ]),
                                                html.Div(id="track-lap-control-3", children=[
                                                    html.Label(id="track-lap-label-3", style=_LABEL_STYLE),
                                                    dcc.Dropdown(id="track-lap-dropdown-3", options=[], value=None, clearable=False),
                                                ]),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                            html.Div(
                                className="track-map-graphs-grid",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr",
                                    "gap": "16px",
                                    "marginBottom": "20px",
                                    "minWidth": "0",
                                    "overflow": "hidden",
                                },
                                children=[
                                    dcc.Loading(
                                        id="loading-trackmap-graph",
                                        className="track-map-loading",
                                        style={"minWidth": "0", "width": "100%", "overflow": "hidden"},
                                        type="circle",
                                        children=dcc.Graph(
                                            id="trackmap-graph",
                                            figure=empty_fig("Track Map"),
                                            hoverData=None,
                                            clear_on_unhover=True,
                                            config={"responsive": True},
                                            responsive=True,
                                            className="track-map-graph",
                                            style={"cursor": "crosshair", "width": "100%", "minWidth": "0"},
                                        ),
                                    ),
                                    dcc.Loading(
                                        id="loading-gear-map-graph",
                                        className="track-map-loading",
                                        style={"minWidth": "0", "width": "100%", "overflow": "hidden"},
                                        type="circle",
                                        children=dcc.Graph(
                                            id="gear-map-graph",
                                            figure=empty_fig("Gear Shifts on Track"),
                                            hoverData=None,
                                            clear_on_unhover=True,
                                            config={"responsive": True},
                                            responsive=True,
                                            className="track-map-graph",
                                            style={"cursor": "crosshair", "width": "100%", "minWidth": "0"},
                                        ),
                                    ),
                                ],
                            ),

                        ],
                    ),
                ],
            ),
        ],
    )


def create_layout():
    return html.Div(
        style={"background": _BG, "minHeight": "100vh", "margin": "0"},
        children=[
            dcc.Store(id="user-store", storage_type="local"),
            _login_page(),
            _dashboard_page(),
        ],
    )
