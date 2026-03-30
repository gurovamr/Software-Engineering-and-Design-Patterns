from dash import Dash
from src.dash_layout import create_layout
from src.dash_callbacks import register_callbacks

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = create_layout()
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)