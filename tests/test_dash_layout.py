"""UI structure tests for src.dash_layout."""

from dash import html, dash_table
import plotly.graph_objects as go

from src.dash_layout import (
    empty_fig,
    _section_title,
    _login_page,
    _podium_card,
    _sidebar,
    _results_table,
    _lap_table_panel,
    _dashboard_page,
    create_layout,
)


class TestEmptyFig:
    def test_empty_fig_returns_figure(self):
        fig = empty_fig("Test Title")
        assert isinstance(fig, go.Figure)

    def test_empty_fig_has_title(self):
        fig = empty_fig("Test Title")
        assert fig.layout.title.text == "Test Title"


class TestSectionTitle:
    def test_section_title_returns_div(self):
        result = _section_title("Test")
        assert isinstance(result, html.Div)


class TestLoginPage:
    def test_login_page_has_expected_ids(self):
        page = _login_page()
        assert page.id == "login-page"
        ids = []

        def collect_ids(comp):
            if hasattr(comp, "id") and comp.id:
                ids.append(comp.id)
            if hasattr(comp, "children"):
                children = comp.children
                if isinstance(children, list):
                    for c in children:
                        collect_ids(c)
                elif children is not None:
                    collect_ids(children)

        collect_ids(page)
        for expected in ["login-name", "login-password", "btn-login", "btn-register"]:
            assert expected in ids


class TestPodiumCard:
    def test_podium_card_contains_name_and_team_ids(self):
        card = _podium_card("podium-p1", "P1", "#FFD700")
        ids = []

        def collect_ids(comp):
            if hasattr(comp, "id") and comp.id:
                ids.append(comp.id)
            if hasattr(comp, "children"):
                children = comp.children
                if isinstance(children, list):
                    for c in children:
                        collect_ids(c)
                elif children is not None:
                    collect_ids(children)

        collect_ids(card)
        assert "podium-p1-name" in ids
        assert "podium-p1-team" in ids


class TestSidebar:
    def test_sidebar_contains_core_controls(self):
        sidebar = _sidebar()
        ids = []

        def collect_ids(comp):
            if hasattr(comp, "id") and comp.id:
                ids.append(comp.id)
            if hasattr(comp, "children"):
                children = comp.children
                if isinstance(children, list):
                    for c in children:
                        collect_ids(c)
                elif children is not None:
                    collect_ids(children)

        collect_ids(sidebar)
        expected = [
            "year-input",
            "event-input",
            "session-input",
            "load-button",
            "load-full-event-button",
        ]
        for eid in expected:
            assert eid in ids


class TestResultsTable:
    def _find_datatable(self, comp):
        if isinstance(comp, dash_table.DataTable):
            return comp
        if hasattr(comp, "children"):
            children = comp.children
            if isinstance(children, list):
                for c in children:
                    found = self._find_datatable(c)
                    if found is not None:
                        return found
            elif children is not None:
                return self._find_datatable(children)
        return None

    def test_results_table_contains_datatable_with_id(self):
        container = _results_table()
        table = self._find_datatable(container)
        assert table is not None
        assert table.id == "results-table"


class TestLapTablePanel:
    def test_lap_table_panel_hidden_initially(self):
        panel = _lap_table_panel(1)
        assert panel.id == "lap-table-panel-1"
        assert isinstance(panel, html.Div)
        assert panel.style.get("display") == "none"


class TestDashboardPage:
    def _collect_ids(self, comp):
        ids = []
        if hasattr(comp, "id") and comp.id:
            ids.append(comp.id)
        if hasattr(comp, "children"):
            children = comp.children
            if isinstance(children, list):
                for c in children:
                    ids.extend(self._collect_ids(c))
            elif children is not None:
                ids.extend(self._collect_ids(children))
        return ids

    def test_dashboard_page_contains_core_graph_ids(self):
        page = _dashboard_page()
        ids = self._collect_ids(page)
        expected = [
            "dashboard-page",
            "session-header",
            "position-chart-graph",
            "lap-summary-graph",
            "speed-graph",
            "gear-graph",
            "inputs-graph",
            "trackmap-graph",
            "gear-map-graph",
        ]
        for eid in expected:
            assert eid in ids


class TestCreateLayout:
    def _collect_ids(self, comp):
        ids = []
        if hasattr(comp, "id") and comp.id:
            ids.append(comp.id)
        if hasattr(comp, "children"):
            children = comp.children
            if isinstance(children, list):
                for c in children:
                    ids.extend(self._collect_ids(c))
            elif children is not None:
                ids.extend(self._collect_ids(children))
        return ids

    def test_layout_exposes_login_and_dashboard_pages(self):
        layout = create_layout()
        ids = self._collect_ids(layout)
        for eid in ["user-store", "login-page", "dashboard-page"]:
            assert eid in ids
