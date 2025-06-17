from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
from app.services.importers import get_importer
from app.services.validators import validate_address_cep
from app.utils.normalize import normalize_cep, normalize_text
import csv
import io
import os

main_routes = Blueprint('main', __name__)

@main_routes.route('/', methods=['GET'])
def home():
    session.clear()
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    if 'preview_loaded' not in session:
        session.clear()
        session['lista'] = []
        session['preview_loaded'] = True
        session.modified = True

    enderecos_brutos = request.form.get('enderecos', '')
    if not enderecos_brutos.strip():
        return jsonify({"success": False, "msg": "Nenhum endereço fornecido"}), 400

    linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
    lista_preview_novos = []

    # Parse de blocos de endereços no formato esperado (Paack etc)
    i = 0
    while i < len(linhas) - 2:
        linha = linhas[i]
        cep = None
        # Extrai o CEP por regex (Portugal)
        import re
        cep_match = re.search(r'(\d{4}-\d{3})', linha)
        if cep_match:
            cep = cep_match.group(1)
        if cep:
            numero_pacote_str = linhas[i+3] if (i+3) < len(linhas) else ""
            numero_pacote = numero_pacote_str if numero_pacote_str.isdigit() else ""
            res = validate_address_cep(linha, cep)
            novo = {
                "order_number": numero_pacote,
                "address": linha,
                "cep": cep,
                **res,
                "importacao_tipo": "manual"
            }
            lista_preview_novos.append(novo)
            i += 4
        else:
            i += 1

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
        importer = get_importer(empresa)
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
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "order number", "address", "latitude", "longitude", 
            "postal_code", "cor", "rua_google", "freguesia_google", "status"
        ])
        for row in lista_para_csv:
            status = "Validado" if row.get("cep_ok") and row.get("rua_bate") else "Divergente"
            writer.writerow([
                row.get("order_number", ""),
                row.get("address", ""),
                row.get("latitude", ""),
                row.get("longitude", ""),
                row.get("postal_code_encontrado") or row.get("cep", ""),
                row.get("cor", ""),
                row.get("rua_google", ""),
                row.get("freguesia", ""),
                status
            ])
        csv_content = output.getvalue()
        session['csv_content'] = csv_content
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
