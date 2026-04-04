from dash import Dash
from src.dash_layout import create_layout
from src.dash_callbacks import DashCallbacks

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    update_title="Loading...",
)
server = app.server

app.layout = create_layout()
DashCallbacks.register(app)

if __name__ == "__main__":
    app.run(debug=True)