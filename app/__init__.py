import os
from flask import Flask
from app.utils.models import db
from app.utils.routes import main_routes

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")
    app.config['SESSION_COOKIE_NAME'] = 'drivemaps_session'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enderecos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    app.register_blueprint(main_routes)
    return app
