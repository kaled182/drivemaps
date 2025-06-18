# app/routes/__init__.py

from flask import Blueprint
from .importacao import importacao_bp as import_routes
from .preview import preview_routes
from .gerar import gerar_routes
from .api import api_routes

# Cria um blueprint principal para rotas
main_routes = Blueprint('main', __name__)

# Registra os sub-blueprints de rotas específicas
main_routes.register_blueprint(import_routes)
main_routes.register_blueprint(preview_routes)
main_routes.register_blueprint(gerar_routes)
main_routes.register_blueprint(api_routes)
