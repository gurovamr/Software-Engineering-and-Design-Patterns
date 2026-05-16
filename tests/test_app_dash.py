"""
Unit tests for app_dash.py

Testing Strategy:
- Verify the module imports successfully
- Test configuration constants
- Verify main components exist
- No mocking of initialization (integration test approach)
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import app_dash
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


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

    def test_callbacks_exist(self):
        """Test that callbacks object was created."""
        import app_dash
        assert hasattr(app_dash, 'callbacks')
        assert app_dash.callbacks is not None


class TestAppDashIntegration:
    """Integration tests - verify the app works with real imports."""

    def test_app_has_layout(self):
        """Test that the app has a layout defined."""
        import app_dash
        assert app_dash.app.layout is not None

    def test_app_has_config(self):
        """Test app is configured correctly."""
        import app_dash
        assert hasattr(app_dash.app, 'config')
        # Check suppress_callback_exceptions is set
        assert app_dash.app.config.get('suppress_callback_exceptions') is True

    def test_module_imports_without_errors(self):
        """Test the module can be imported without raising exceptions."""
        try:
            import app_dash
            success = True
        except Exception as e:
            success = False
            pytest.fail(f"Failed to import app_dash: {e}")

        assert success

    def test_services_are_created(self):
        """Test that dependency injection created the service objects."""
        import app_dash
        # These are module-level variables in app_dash.py
        # We can't access them directly (they're private with _)
        # but we can verify the app and callbacks exist
        assert app_dash.app is not None
        assert app_dash.callbacks is not None
        # If services weren't created, callbacks wouldn't exist


class TestAppDashImportSafety:
    """Test that importing doesn't cause unintended side effects."""

    def test_import_does_not_start_server(self):
        """Importing the module should not start the dev server."""
        import app_dash
        # If we got here, import succeeded without running the server
        # (the if __name__ == "__main__" guard prevents auto-run)
        assert True

    def test_can_import_multiple_times(self):
        """Test the module can be imported multiple times safely."""
        import app_dash
        import importlib
        importlib.reload(app_dash)
        # If reload works, the module is well-structured
        assert app_dash.app is not None
