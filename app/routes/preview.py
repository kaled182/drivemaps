# app/routes/preview.py

from flask import Blueprint, render_template, session
import os

preview_bp = Blueprint('preview', __name__)

@preview_bp.route("/", methods=["GET"])
def home():
    """Exibe a página inicial de importação e limpa a sessão antiga."""
    session.clear()
    return render_template("index.html")

@preview_bp.route("/preview", methods=["GET"])
def preview_page():
    """
    Exibe a página de visualização com o mapa e a tabela,
    utilizando os dados que já estão na sessão.
    """
    lista = session.get('lista', [])
    origens = list(set(item.get('importacao_tipo', 'manual') for item in lista))
    
    return render_template(
        "preview.html",
        lista=lista,
        GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
        origens=origens
    )
