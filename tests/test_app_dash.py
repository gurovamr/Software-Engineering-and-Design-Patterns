"""
Unit tests for app_dash.py

Testing Strategy:
- Test app initialization without actually running the server
- Verify dependency injection is set up correctly
- Mock external dependencies (services, database)
- Test that callbacks are registered
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAppDashInitialization:
    """Test the Dash app initialization and setup."""

    @patch('app_dash.AuthService')
    @patch('app_dash.DriverService')
    @patch('app_dash.DataLoader')
    @patch('app_dash.SessionService')
    @patch('app_dash.create_layout')
    @patch('app_dash.DashboardCallbackRegistry')
    def test_app_initialization(
        self,
        mock_callback_registry,
        mock_create_layout,
        mock_session_service,
        mock_data_loader,
        mock_driver_service,
        mock_auth_service
    ):
        """Test that the Dash app initializes with all dependencies."""
        # Arrange: Set up mocks
        mock_create_layout.return_value = Mock()
        mock_registry_instance = Mock()
        mock_callback_registry.return_value = mock_registry_instance

        # Act: Import the module (which initializes the app)
        # We need to reload to trigger initialization with our mocks
        import importlib
        import app_dash
        importlib.reload(app_dash)

        # Assert: Verify services were instantiated with correct parameters
        mock_auth_service.assert_called_once_with(db_path="data/f1.sqlite")
        mock_driver_service.assert_called_once_with(db_path="data/f1.sqlite")
        mock_data_loader.assert_called_once()
        mock_session_service.assert_called_once_with(
            db_path="data/f1.sqlite",
            cache_dir="cache"
        )

    @patch('app_dash.AuthService')
    @patch('app_dash.DriverService')
    @patch('app_dash.DataLoader')
    @patch('app_dash.SessionService')
    @patch('app_dash.DashboardCallbackRegistry')
    def test_callbacks_registered(
        self,
        mock_callback_registry,
        mock_session_service,
        mock_data_loader,
        mock_driver_service,
        mock_auth_service
    ):
        """Test that callbacks are registered with the app."""
        # Arrange
        mock_registry_instance = Mock()
        mock_callback_registry.return_value = mock_registry_instance

        # Act
        import importlib
        import app_dash
        importlib.reload(app_dash)

        # Assert: Verify DashboardCallbackRegistry was instantiated with services
        mock_callback_registry.assert_called_once()
        call_kwargs = mock_callback_registry.call_args[1]

        assert 'auth_service' in call_kwargs
        assert 'driver_service' in call_kwargs
        assert 'data_loader' in call_kwargs
        assert 'session_service' in call_kwargs

        # Verify register was called with the app
        mock_registry_instance.register.assert_called_once()

    @patch('app_dash.Dash')
    def test_dash_app_configuration(self, mock_dash):
        """Test that Dash app is configured with correct parameters."""
        # Arrange
        mock_app_instance = Mock()
        mock_dash.return_value = mock_app_instance

        # Act
        import importlib
        import app_dash
        importlib.reload(app_dash)

        # Assert: Verify Dash was initialized with correct settings
        mock_dash.assert_called_once_with(
            '__main__',
            suppress_callback_exceptions=True,
            update_title="Loading..."
        )

    def test_db_path_constant(self):
        """Test that DB_PATH is set correctly."""
        import app_dash
        assert app_dash.DB_PATH == "data/f1.sqlite"


class TestAppDashServer:
    """Test the Flask server setup."""

    @patch('app_dash.Dash')
    def test_server_attribute_exists(self, mock_dash):
        """Test that the server attribute is exposed."""
        # Arrange
        mock_app_instance = Mock()
        mock_app_instance.server = Mock()
        mock_dash.return_value = mock_app_instance

        # Act
        import importlib
        import app_dash
        importlib.reload(app_dash)

        # Assert
        assert hasattr(app_dash, 'server')
        assert app_dash.server == mock_app_instance.server


# Integration-style test (runs when file is executed directly)
class TestAppDashIntegration:
    """Integration tests that verify app can be created (but not run)."""

    @pytest.mark.skipif(True, reason="Requires database file to exist")
    def test_app_can_be_created_with_real_dependencies(self):
        """
        This test would verify the app can actually be created.
        Skip by default since it requires the database file.
        """
        import app_dash
        assert app_dash.app is not None
        assert app_dash.app.layout is not None
