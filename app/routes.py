from flask import Blueprint, request, jsonify, session
from app.services.importers import get_importer
import os

main_routes = Blueprint('main', __name__)

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()
        if not file or not empresa:
            return jsonify({"success": False, "msg": "Arquivo ou empresa não especificados"}), 400
        importer = get_importer(empresa)
        novos_itens = importer.parse(file)
        lista_atual = session.get('lista', [])
        # Dedupe: pode implementar lógica melhor
        for item in novos_itens:
            if item not in lista_atual:
                lista_atual.append(item)
        session['lista'] = lista_atual
        session.modified = True
        return jsonify({
            "success": True,
            "lista": lista_atual,
            "origens": list({i.get("importacao_tipo", "manual") for i in lista_atual}),
            "total": len(lista_atual)
        })
    except Exception as e:
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500
