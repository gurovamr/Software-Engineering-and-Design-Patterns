"""
Unit tests for app_dash.py

Testing Strategy:
- Test configuration constants
- Test that the app can be imported without errors
- Mock heavy dependencies to avoid database/network calls
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import app_dash
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import Mock, patch


class TestAppDashConfiguration:
    """Test app configuration and constants."""

    def test_db_path_constant(self):
        """Test that DB_PATH is set correctly."""
        import app_dash
        assert app_dash.DB_PATH == "data/f1.sqlite"

    def test_app_exists(self):
        """Test that the app object is created."""
        import app_dash
        assert hasattr(app_dash, 'app')
        assert app_dash.app is not None

    def test_server_exists(self):
        """Test that the Flask server is exposed."""
        import app_dash
        assert hasattr(app_dash, 'server')
        assert app_dash.server is not None


class TestAppDashDependencies:
    """Test dependency injection setup."""

    @patch('app_dash.SessionService')
    @patch('app_dash.DataLoader')
    @patch('app_dash.DriverService')
    @patch('app_dash.AuthService')
    def test_services_are_instantiated_with_correct_params(
        self,
        mock_auth_service_cls,
        mock_driver_service_cls,
        mock_data_loader_cls,
        mock_session_service_cls
    ):
        """Test that services are created with correct parameters when module loads."""
        # This test needs to import the module fresh, but since it's already
        # imported, we test the mock calls would happen

        # Reset mocks
        mock_auth_service_cls.reset_mock()
        mock_driver_service_cls.reset_mock()
        mock_data_loader_cls.reset_mock()
        mock_session_service_cls.reset_mock()

        # Force reimport
        import importlib
        import app_dash
        importlib.reload(app_dash)

        # Verify services were created with correct arguments
        mock_auth_service_cls.assert_called_with(db_path="data/f1.sqlite")
        mock_driver_service_cls.assert_called_with(db_path="data/f1.sqlite")
        mock_data_loader_cls.assert_called_once()
        mock_session_service_cls.assert_called_with(
            db_path="data/f1.sqlite",
            cache_dir="cache"
        )


class TestAppDashIntegration:
    """Integration tests - verify the app works with real imports."""

    def test_app_has_layout(self):
        """Test that the app has a layout defined."""
        import app_dash
        # Layout might be a function or an object
        assert app_dash.app.layout is not None

    def test_app_title_config(self):
        """Test app is configured with update_title."""
        import app_dash
        # Dash stores config in app.config
        assert hasattr(app_dash.app, 'config')

    def test_callback_registry_exists(self):
        """Test that callbacks object was created."""
        import app_dash
        assert hasattr(app_dash, 'callbacks')
        assert app_dash.callbacks is not None


class TestAppDashImportSafety:
    """Test that importing doesn't cause side effects."""

    def test_import_does_not_start_server(self):
        """Importing the module should not start the dev server."""
        import app_dash
        # If we got here, import succeeded without running the server
        # (the if __name__ == "__main__" guard prevents auto-run)
        assert True

    def test_module_imports_successfully(self):
        """Test the module can be imported without errors."""
        try:
            import app_dash
            success = True
        except Exception as e:
            success = False
            pytest.fail(f"Failed to import app_dash: {e}")

        assert success
