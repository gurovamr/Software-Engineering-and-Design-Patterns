from datetime import date

from dash import html, dcc, dash_table
import plotly.graph_objects as go

_current_year = date.today().year

# ── Dark theme colors ───────────────────────────────────────────
_BG = "#0d0d1a"
_CARD_BG = "#1a1a2e"
_ACCENT = "#e10600"
_TEXT = "#e0e0e0"
_MUTED = "#888"
_BORDER = "#333"


def empty_fig(title: str):
    fig = go.Figure()
    fig.update_layout(
        title=title, height=350,
        paper_bgcolor=_CARD_BG, plot_bgcolor=_CARD_BG,
        font=dict(color=_TEXT),
    )
    return fig


def _login_page():
    return html.Div(
        id="login-page",
        style={
            "maxWidth": "400px", "margin": "120px auto", "padding": "30px",
            "background": _CARD_BG, "borderRadius": "12px",
            "border": f"1px solid {_BORDER}", "color": _TEXT,
        },
        children=[
            html.H2("🏎 F1 Telemetry – Login", style={"color": _ACCENT}),
            html.Label("Username", style={"color": _TEXT}),
            dcc.Input(id="login-name", type="text", placeholder="Enter username",
                      style={"width": "100%", "marginBottom": "12px", "background": _BG, "color": _TEXT, "border": f"1px solid {_BORDER}"}),
            html.Label("Password", style={"color": _TEXT}),
            dcc.Input(id="login-password", type="password", placeholder="Enter password",
                      style={"width": "100%", "marginBottom": "12px", "background": _BG, "color": _TEXT, "border": f"1px solid {_BORDER}"}),
            html.Label("Favorite Driver (optional)", style={"color": _TEXT}),
            dcc.Dropdown(id="login-fav-driver", options=[], value=None, placeholder="Select driver…",
                         style={"marginBottom": "16px"}),
            html.Div(style={"display": "flex", "gap": "10px"}, children=[
                html.Button("Login", id="btn-login", n_clicks=0,
                            style={"background": _ACCENT, "color": "white", "border": "none", "padding": "8px 20px", "borderRadius": "4px", "cursor": "pointer"}),
                html.Button("Register", id="btn-register", n_clicks=0,
                            style={"background": _BORDER, "color": _TEXT, "border": "none", "padding": "8px 20px", "borderRadius": "4px", "cursor": "pointer"}),
            ]),
            html.Div(id="login-message", style={"color": "#ff6b6b", "marginTop": "10px"}),
        ],
    )


_CARD_STYLE = {
    "background": _CARD_BG, "borderRadius": "10px", "padding": "16px",
    "border": f"1px solid {_BORDER}",
}

_LABEL_STYLE = {"color": _MUTED, "fontSize": "0.85em", "marginBottom": "4px"}

_KPI_STYLE = {
    **_CARD_STYLE,
    "textAlign": "center", "padding": "12px",
}


def _podium_card(card_id, rank_label, rank_color):
    return html.Div(id=card_id, style={
        **_CARD_STYLE, "textAlign": "center", "minWidth": "160px", "flex": "1",
    }, children=[
        html.Div(rank_label, style={
            "fontSize": "0.75em", "fontWeight": "bold", "color": rank_color,
            "textTransform": "uppercase", "marginBottom": "6px",
        }),
        html.Div("—", id=f"{card_id}-name", style={"fontSize": "1.1em", "fontWeight": "bold", "color": _TEXT}),
        html.Div("", id=f"{card_id}-team", style={"fontSize": "0.8em", "color": _MUTED}),
    ])


def _dashboard_page():
    return html.Div(
        id="dashboard-page",
        style={"display": "none", "background": _BG, "color": _TEXT, "minHeight": "100vh"},
        children=[
            # ── Sync banner ─────────────────────────────────────
            html.Div(id="sync-status", style={
                "padding": "6px 16px", "textAlign": "center", "fontSize": "0.85em",
            }),
            dcc.Interval(id="sync-interval", interval=2000, disabled=True),

            # ── Top bar ─────────────────────────────────────────
            html.Div(style={
                "display": "flex", "justifyContent": "space-between", "alignItems": "center",
                "padding": "10px 24px", "borderBottom": f"1px solid {_BORDER}",
            }, children=[
                html.Div(style={"display": "flex", "alignItems": "center", "gap": "12px"}, children=[
                    html.Span("🏎", style={"fontSize": "1.4em"}),
                    html.Span("F1 Telemetry", style={"fontSize": "1.2em", "fontWeight": "bold", "color": _TEXT}),
                ]),
                html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px"}, children=[
                    html.Span(id="user-greeting", style={"fontSize": "0.85em", "color": _MUTED}),
                    html.Button("Logout", id="btn-logout", n_clicks=0, style={
                        "background": _BORDER, "color": _TEXT, "border": "none",
                        "padding": "4px 14px", "borderRadius": "4px", "cursor": "pointer", "fontSize": "0.8em",
                    }),
                ]),
            ]),

            # ── Main content ────────────────────────────────────
            html.Div(style={"display": "flex", "minHeight": "calc(100vh - 60px)"}, children=[

                # ── Sidebar ─────────────────────────────────────
                html.Div(style={
                    "width": "280px", "padding": "20px", "background": _CARD_BG,
                    "borderRight": f"1px solid {_BORDER}", "flexShrink": "0",
                }, children=[
                    html.Label("Year", style=_LABEL_STYLE),
                    dcc.Input(id="year-input", type="number", value=_current_year, min=2018, max=_current_year,
                              style={"width": "100%", "marginBottom": "12px", "background": _BG, "color": _TEXT,
                                     "border": f"1px solid {_BORDER}", "borderRadius": "4px", "padding": "6px"}),

                    html.Label("Race / Event", style=_LABEL_STYLE),
                    dcc.Dropdown(id="event-input", options=[], value=None, placeholder="Select event…",
                                 style={"marginBottom": "12px"}),

                    html.Label("Session", style=_LABEL_STYLE),
                    dcc.Dropdown(
                        id="session-input",
                        options=[{"label": s, "value": s} for s in ["R", "Q", "FP1", "FP2", "FP3", "S", "SQ"]],
                        value="R", clearable=False,
                        style={"marginBottom": "16px"},
                    ),

                    dcc.Loading(id="loading-session", type="circle", children=
                        html.Button("Load Session", id="load-button", n_clicks=0, style={
                            "width": "100%", "background": _ACCENT, "color": "white", "border": "none",
                            "padding": "10px", "borderRadius": "6px", "cursor": "pointer", "fontWeight": "bold",
                        }),
                    ),

                    html.Hr(style={"borderColor": _BORDER, "margin": "20px 0"}),

                    html.Label("Selected Driver", style=_LABEL_STYLE),
                    dcc.Dropdown(id="driver-dropdown", options=[], value=None, clearable=False,
                                 style={"marginBottom": "12px"}),

                    html.Label("Laps to compare", style=_LABEL_STYLE),
                    dcc.Dropdown(id="lap-dropdown", options=[], value=[], multi=True),

                    html.Hr(style={"borderColor": _BORDER, "margin": "20px 0"}),

                    html.Label("Compare with Driver", style=_LABEL_STYLE),
                    dcc.Dropdown(id="compare-driver-dropdown", options=[], value=None,
                                 placeholder="Select 2nd driver…",
                                 style={"marginBottom": "12px"}),

                    dcc.Store(id="bundle-store"),
                    dcc.Store(id="results-store"),
                ]),

                # ── Content area ────────────────────────────────
                html.Div(style={"flex": "1", "padding": "20px", "overflowY": "auto"}, children=[

                    # Session header
                    html.Div(id="session-header", style={
                        "fontSize": "1.4em", "fontWeight": "bold", "color": _TEXT, "marginBottom": "16px",
                    }),

                    # ── Podium cards ────────────────────────────
                    html.Div(style={"display": "flex", "gap": "12px", "marginBottom": "20px", "flexWrap": "wrap"}, children=[
                        _podium_card("podium-p1", "P1 — Winner", "#FFD700"),
                        _podium_card("podium-p2", "P2", "#C0C0C0"),
                        _podium_card("podium-p3", "P3", "#CD7F32"),
                        _podium_card("podium-fastest", "⚡ Fastest Lap", "#a855f7"),
                    ]),

                    # ── KPI row ─────────────────────────────────
                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr", "gap": "10px", "marginBottom": "20px"}, children=[
                        html.Div(id="kpi-laps", style=_KPI_STYLE),
                        html.Div(id="kpi-max-speed", style=_KPI_STYLE),
                        html.Div(id="kpi-samples", style=_KPI_STYLE),
                        html.Div(id="kpi-best-lap", style=_KPI_STYLE),
                    ]),

                    # ── Position chart ──────────────────────────
                    dcc.Graph(id="position-chart-graph", figure=empty_fig("Race Timeline – Position Chart"),
                              style={"marginBottom": "20px"}),

                    # ── Finishing order table ───────────────────
                    html.Div(style={**_CARD_STYLE, "marginBottom": "20px", "padding": "0", "overflow": "hidden"}, children=[
                        html.Div("Finishing Order", style={
                            "padding": "12px 16px", "fontWeight": "bold", "fontSize": "1em",
                            "borderBottom": f"1px solid {_BORDER}",
                        }),
                        dash_table.DataTable(
                            id="results-table",
                            columns=[], data=[],
                            row_selectable="single", selected_rows=[],
                            style_table={"overflowX": "auto"},
                            style_header={
                                "backgroundColor": _CARD_BG, "color": _TEXT, "fontWeight": "bold",
                                "border": f"1px solid {_BORDER}",
                            },
                            style_cell={
                                "backgroundColor": _BG, "color": _TEXT, "border": f"1px solid {_BORDER}",
                                "padding": "8px 12px", "fontSize": "0.9em", "textAlign": "left",
                            },
                            style_data_conditional=[
                                {"if": {"state": "active"}, "backgroundColor": "#2a2a4e", "border": f"1px solid {_ACCENT}"},
                                {"if": {"state": "selected"}, "backgroundColor": "#2a2a4e", "border": f"1px solid {_ACCENT}"},
                            ],
                        ),
                    ]),

                    # ── Key Events ──────────────────────────────
                    html.Div(style={**_CARD_STYLE, "marginBottom": "20px"}, children=[
                        html.Div("Key Events", style={"fontWeight": "bold", "marginBottom": "10px", "fontSize": "1em"}),
                        html.Div(id="key-events-container", style={
                            "display": "flex", "flexWrap": "wrap", "gap": "8px",
                        }),
                    ]),

                    # ── Tyre Strategy ───────────────────────
                    dcc.Graph(id="tyre-strategy-graph", figure=empty_fig("Tyre Strategy"),
                              style={"marginBottom": "20px"}),

                    # ── Team Pace + Lap Distribution ────────
                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginBottom": "20px"}, children=[
                        dcc.Graph(id="team-pace-graph", figure=empty_fig("Team Pace Comparison")),
                        dcc.Graph(id="laptimes-dist-graph", figure=empty_fig("Lap Times Distribution")),
                    ]),

                    # ── Driver Comparison ────────────────────
                    html.Div(id="comparison-section", style={**_CARD_STYLE, "marginBottom": "20px", "display": "none"}, children=[
                        dcc.Graph(id="comparison-graph", figure=empty_fig("Driver Comparison")),
                    ]),

                    # ── Telemetry section ───────────────────────
                    html.Div(style={**_CARD_STYLE, "marginBottom": "20px"}, children=[
                        html.Div("Lap Comparison", style={"fontWeight": "bold", "marginBottom": "8px"}),
                        dcc.Graph(id="lap-summary-graph", figure=empty_fig("Lap Comparison")),
                    ]),

                    dash_table.DataTable(
                        id="lap-summary-table", columns=[], data=[],
                        style_table={"overflowX": "auto", "marginBottom": "20px"},
                        style_header={"backgroundColor": _CARD_BG, "color": _TEXT, "fontWeight": "bold", "border": f"1px solid {_BORDER}"},
                        style_cell={"backgroundColor": _BG, "color": _TEXT, "border": f"1px solid {_BORDER}", "padding": "6px 10px", "fontSize": "0.85em"},
                    ),

                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginBottom": "20px"}, children=[
                        dcc.Graph(id="speed-graph", figure=empty_fig("Speed")),
                        dcc.Graph(id="gear-graph", figure=empty_fig("Gear")),
                    ]),
                    dcc.Graph(id="inputs-graph", figure=empty_fig("Throttle / Brake"), style={"marginBottom": "20px"}),
                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginBottom": "20px"}, children=[
                        dcc.Graph(id="trackmap-graph", figure=empty_fig("Track Map")),
                        dcc.Graph(id="gear-map-graph", figure=empty_fig("Gear Shifts on Track")),
                    ]),
                ]),
            ]),
        ],
    )


def create_layout():
    return html.Div(style={"background": _BG, "minHeight": "100vh", "margin": "0"}, children=[
        dcc.Store(id="user-store", storage_type="local"),
        _login_page(),
        _dashboard_page(),
    ])