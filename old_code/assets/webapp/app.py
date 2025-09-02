import dash
import dash_bootstrap_components as dbc
import dash_auth

from .layout import create_layout
from .callbacks import register_callbacks

def create_app(authentication=True):
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        assets_folder='assets'
    )
    app.title = "Process Analysis"

    if authentication:
        USERNAME_PASSWORD_PAIRS = [['admin', 'admin132456.'], ['user1', 'heattransplan132456.']]
        auth = dash_auth.BasicAuth(app, USERNAME_PASSWORD_PAIRS)

    app.layout = create_layout()
    register_callbacks(app)
    
    return app

def application(authentication=True):
    app = create_app(authentication)
    return app.server 