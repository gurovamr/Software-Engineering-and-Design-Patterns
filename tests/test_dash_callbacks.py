"""Helper and wiring tests for src.dash_callbacks."""

from unittest.mock import Mock

import pandas as pd
import plotly.graph_objects as go

from src.dash_callbacks import DashboardCallbackRegistry
from src.auth_service import AuthService, DriverService
from src.preload_service import DataLoader
from src.session_service import SessionService


def _make_registry():
    auth = Mock(spec=AuthService)
    driver_service = Mock(spec=DriverService)
    loader = Mock(spec=DataLoader)
    session_service = Mock(spec=SessionService)
    return DashboardCallbackRegistry(auth, driver_service, loader, session_service)


class TestRegistryInit:
    def test_init_creates_empty_cache(self):
        reg = _make_registry()
        # registry uses a private dict _session_cache
        cache = getattr(reg, "_session_cache", None)
        assert isinstance(cache, dict)
        assert cache == {}


class TestCleanTelemetry:
    def test_clean_telemetry_empty_returns_empty(self):
        reg = _make_registry()
        df = pd.DataFrame()
        out = reg._clean_telemetry_dataframe(df)
        assert out.empty

    def test_clean_telemetry_casts_driver_and_lapnumber(self):
        reg = _make_registry()
        df = pd.DataFrame({"Driver": [1], "LapNumber": ["1"], "Distance": [0.0]})
        out = reg._clean_telemetry_dataframe(df)
        assert not out.empty
        assert out["Driver"].dtype == object
        assert pd.api.types.is_integer_dtype(out["LapNumber"])


class TestSessionCache:
    def test_store_and_retrieve_bundle_roundtrip(self):
        reg = _make_registry()
        bundle = Mock()
        bundle.telemetry = pd.DataFrame({"Driver": ["VER"], "LapNumber": [1]})

        key = reg._store_session_bundle(2024, "Monaco", "R", bundle)
        cache = getattr(reg, "_session_cache", {})
        assert key in cache

        data = {"cache_key": key}
        got_bundle, tel = reg._retrieve_cached_bundle(data)
        assert got_bundle is bundle
        assert isinstance(tel, pd.DataFrame)


class TestEmptyDashboard:
    def test_empty_dashboard_tuple_shape(self):
        reg = _make_registry()
        result = reg._empty_dashboard()

        # Expected length: 12 items
        assert isinstance(result, tuple)
        assert len(result) == 12

        # First four are KPI strings
        for s in result[:4]:
            assert isinstance(s, str)

        # Next six are Plotly figures
        for fig in result[4:10]:
            assert isinstance(fig, go.Figure)

        # Last element is currently a placeholder (None)
        assert result[10] is None


class TestRegister:
    def test_register_attaches_some_callbacks(self):
        reg = _make_registry()
        mock_app = Mock()

        def fake_callback(*_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

        mock_app.callback = Mock(side_effect=fake_callback)
        reg.register(mock_app)
        # We only assert that some callbacks were registered
        assert mock_app.callback.call_count > 0
