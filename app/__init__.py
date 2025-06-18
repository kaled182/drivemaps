# app/__init__.py

from flask import Flask
from flask_session import Session
from .routes import register_routes

def create_app():
    app = Flask(__name__)
    
    # Configurações da aplicação
    app.config.from_object('config.Config')

    # Inicializa sessão do Flask
    Session(app)

    # Registra os blueprints das rotas
    register_routes(app)

    return app
