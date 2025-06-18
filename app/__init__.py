# app/__init__.py

from flask import Flask
from flask_session import Session
from .routes import register_routes


def create_app():
    app = Flask(__name__)
    # Carrega configurações PRIMEIRO
    app.config.from_object('config.Config')
    # Verifica se o diretório de sessão existe
    if app.config['SESSION_TYPE'] == 'filesystem':
        import os
        if not os.path.exists(app.config['SESSION_FILE_DIR']):
            os.makedirs(app.config['SESSION_FILE_DIR'])
    # Inicializa a sessão DEPOIS das configurações
    sess = Session()
    sess.init_app(app)
    # Registra rotas
    register_routes(app)
    return app
