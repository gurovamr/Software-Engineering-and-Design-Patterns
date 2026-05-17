from dash import Dash
from pathlib import Path
from src.dash_layout import create_layout
from src.dash_callbacks import DashboardCallbackRegistry
from src.auth_service import AuthService, DriverService
from src.preload_service import DataLoader
from src.session_service import SessionService

DB_PATH = "data/f1.sqlite"
ASSETS_FOLDER = str(Path(__file__).resolve().parent / "assets")

# ── Dependency Injection setup ─────────────────────────────────────────────
# Each service is instantiated once here and injected where needed.
# No global state leaks into callback or service code.
_auth_service = AuthService(db_path=DB_PATH)
_driver_service = DriverService(db_path=DB_PATH)
_data_loader = DataLoader()
_session_service = SessionService(db_path=DB_PATH, cache_dir="cache")

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    update_title="Loading...",
    assets_folder=ASSETS_FOLDER,
)
server = app.server

app.layout = create_layout()

# Wire callbacks with injected services (Facade + DI)
callbacks = DashboardCallbackRegistry(
    auth_service=_auth_service,
    driver_service=_driver_service,
    data_loader=_data_loader,
    session_service=_session_service,
)
callbacks.register(app)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
