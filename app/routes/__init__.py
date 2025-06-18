# app/routes/__init__.py

from flask import Blueprint
from .importacao import importacao_bp
from .preview import preview_bp
from .gerar import gerar_bp
from .api import api_bp

def register_routes(app):
    app.register_blueprint(importacao_bp)
    app.register_blueprint(preview_bp)
    app.register_blueprint(gerar_bp)
    app.register_blueprint(api_bp)
