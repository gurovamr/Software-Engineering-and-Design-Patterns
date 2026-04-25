from dash import Dash
from src.dash_layout import create_layout
from src.dash_callbacks import DashboardCallbackRegistry
from src.auth_service import AuthService, DriverService
from src.preload_service import DataLoader

DB_PATH = "data/f1.sqlite"

# ── Dependency Injection setup ─────────────────────────────────────────────
# Each service is instantiated once here and injected where needed.
# No global state leaks into callback or service code.
_auth_service = AuthService(db_path=DB_PATH)
_driver_service = DriverService(db_path=DB_PATH)
_data_loader = DataLoader()

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    update_title="Loading...",
)
server = app.server

app.layout = create_layout()

# Wire callbacks with injected services (Facade + DI)
callbacks = DashboardCallbackRegistry(
    auth_service=_auth_service,
    driver_service=_driver_service,
    data_loader=_data_loader,
)
callbacks.register(app)

if __name__ == "__main__":
    app.run(debug=True)