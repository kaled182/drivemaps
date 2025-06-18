# app/routes/__init__.py

from flask import Blueprint

from .importacao import importacao_bp as importacao_routes
from .preview import preview_bp as preview_routes
from .gerar import gerar_routes
from .api import api_routes

def register_routes(app):
    app.register_blueprint(importacao_routes)
    app.register_blueprint(preview_routes)
    app.register_blueprint(gerar_routes)
    app.register_blueprint(api_routes)
