# app/__init__.py

from flask import Flask
from flask_session import Session
from .routes import register_routes

def create_app():
    app = Flask(__name__)

    # Carrega configuração da classe Config
    app.config.from_object('config.Config')

    # Inicializa sessão
    Session(app)

    # Registra rotas
    register_routes(app)

    return app
