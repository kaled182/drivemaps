import os
from flask import Flask
from .routes import main_routes

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")
    app.config['SESSION_COOKIE_NAME'] = 'drivemaps_session'
    app.register_blueprint(main_routes)
    return app
