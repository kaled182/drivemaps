# app/__init__.py

from flask import Flask
from flask_session import Session
from .routes import register_routes
from config import Config

def create_app():
    app = Flask(__name__)

    # Configurações
    app.config.from_object(Config)

    # Inicializa sessão
    Session(app)

    # Registra rotas
    register_routes(app)

    return app
