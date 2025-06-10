from flask import Flask
from .routes import main_routes

def create_app():
    app = Flask(__name__)
    app.secret_key = "secret-key-temporaria"  # Substitua por variável de ambiente em produção!
    app.register_blueprint(main_routes)       # ESSENCIAL para rotas funcionarem!
    return app
