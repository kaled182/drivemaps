import os
import io
from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
from app.services.importers import get_importer
from app.services.exporters import export_to_myway
from app.services.validators import validate_address_cep
from app.utils.normalize import normalize_cep

main_routes = Blueprint('main', __name__)

@main_routes.route('/', methods=['GET'])
def home():
    session.clear()
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    session['lista'] = []
    session['preview_loaded'] = True
    session.modified = True

    # Se vier upload de arquivo, é Delnext ou Paack planilha
    if 'planilha' in request.files and request.files['planilha'].filename:
        file = request.files['planilha']
        empresa = request.form.get('empresa', '').lower()
        if not empresa:
            return render_template("home.html", msg="Selecione a empresa antes de importar planilha.")
        importer = get_importer(empresa, input_type='file')
        lista_preview_novos = importer.parse(file)
    else:
        # Caso contrário, assume texto colado no formato Paack
        enderecos_brutos = request.form.get('enderecos', '')
        if not enderecos_brutos.strip():
            return render_template("home.html", msg="Cole endereços ou importe uma planilha.")
        paack_text_importer = get_importer('paack', input_type='text')
        lista_preview_novos = paack_text_importer.parse(enderecos_brutos)

    session['lista'] = lista_preview_novos
    session.modified = True
    origens = list({item.get('importacao_tipo', 'manual') for item in lista_preview_novos})
    return render_template(
        "preview.html",
        lista=lista_preview_novos,
        GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
        origens=origens
    )

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()
        if not file or not empresa:
            return jsonify({"success": False, "msg": "Arquivo ou empresa não especificados"}), 400
        importer = get_importer(empresa, input_type='file')
        novos_itens = importer.parse(file)
        lista_atual = session.get('lista', [])
        # Evita duplicatas
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

@main_routes.route('/api/session-data', methods=['GET'])
def get_session_data():
    try:
        return jsonify({
            "success": True,
            "lista": session.get('lista', []),
            "origens": list({item.get("importacao_tipo", "manual") for item in session.get('lista', [])}),
            "total": len(session.get('lista', []))
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    try:
        data = request.get_json()
        idx = int(data.get('idx', -1))
        endereco = data.get('endereco', '')
        cep = normalize_cep(data.get('cep', ''))

        lista_atual = session.get('lista', [])
        if idx < 0 or idx >= len(lista_atual):
            return jsonify({"success": False, "msg": "Índice inválido"}), 400

        res = validate_address_cep(endereco, cep)
        lista_atual[idx].update({
            "address": endereco,
            "cep": cep,
            **res
        })
        session['lista'] = lista_atual
        session.modified = True

        return jsonify({
            "success": True,
            "item": lista_atual[idx],
            "idx": idx
        })
    except Exception as e:
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500

@main_routes.route('/generate', methods=['POST'])
def generate():
    try:
        lista_para_csv = session.get('lista', [])
        csv_bytes = export_to_myway(lista_para_csv)
        session['csv_content'] = csv_bytes.decode("utf-8")
        session.modified = True
        return redirect(url_for('main.download'))
    except Exception as e:
        return jsonify({"success": False, "msg": f"Erro ao gerar CSV: {str(e)}"}), 500

@main_routes.route('/download')
def download():
    csv_content = session.get('csv_content', '')
    if not csv_content:
        return redirect(url_for('main.home'))
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )
