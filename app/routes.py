from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
import re
import csv
import io
import os
import pandas as pd
import logging
from .utils import valida_rua_google

main_routes = Blueprint('main', __name__)
csv_content = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CORES_IMPORTACAO = [
    "#0074D9",  # Azul - manual
    "#FF851B",  # Laranja - delnext
    "#2ECC40",  # Verde - paack
    "#B10DC9",  # Roxo (não usado por padrão)
    "#FF4136",  # Vermelho (não usado por padrão)
]

ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'txt'}

def extensao_permitida(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalizar(texto):
    import unicodedata
    if not texto:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c)
    ).strip()

def cor_por_tipo(tipo):
    if tipo == "delnext":
        return CORES_IMPORTACAO[1]
    elif tipo == "paack":
        return CORES_IMPORTACAO[2]
    else:
        return CORES_IMPORTACAO[0]

def registro_unico(lista, novo):
    return not any(
        normalizar(item["address"]) == normalizar(novo["address"]) and
        normalizar(item["cep"]) == normalizar(novo["cep"]) and
        item.get("importacao_tipo") == novo.get("importacao_tipo")
        for item in lista
    )

@main_routes.route('/', methods=['GET'])
def home():
    session.clear()
    session['lista'] = []
    session['preview_loaded'] = False
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    try:
        if 'preview_loaded' not in session or not session['preview_loaded']:
            session.clear()
            session['lista'] = []
            session['preview_loaded'] = True
            session.modified = True

        enderecos_brutos = request.form.get('enderecos', '')
        if not enderecos_brutos.strip():
            raise ValueError("Nenhum endereço fornecido")

        regex_cep = re.compile(r'(\d{4}-\d{3})')
        linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
        lista_preview = []
        i = 0
        while i < len(linhas) - 2:
            linha = linhas[i]
            cep_match = regex_cep.search(linha)
            if cep_match:
                if i + 2 < len(linhas) and linhas[i+2] == linha:
                    numero_pacote = linhas[i+3] if (i+3) < len(linhas) else ""
                    cep = cep_match.group(1)
                    res_google = valida_rua_google(linha, cep)
                    rua_digitada = linha.split(',')[0] if linha else ''
                    rua_google = res_google.get('route_encontrada', '')
                    rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
                    cep_ok = cep == res_google.get('postal_code_encontrado', '')
                    lista_preview.append({
                        "order_number": numero_pacote,
                        "address": linha,
                        "cep": cep,
                        "status_google": res_google.get('status'),
                        "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                        "endereco_formatado": res_google.get('endereco_formatado', ''),
                        "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                        "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                        "rua_google": rua_google,
                        "cep_ok": cep_ok,
                        "rua_bate": rua_bate,
                        "freguesia": res_google.get('sublocality', ''),
                        "importacao_tipo": "manual",
                        "cor": cor_por_tipo("manual")
                    })
                    i += 4
                else:
                    i += 1
            else:
                i += 1

        lista_atual = session.get('lista', [])
        for novo in lista_preview:
            if registro_unico(lista_atual, novo):
                lista_atual.append(novo)

        for idx, item in enumerate(lista_atual, 1):
            item['order_number'] = idx

        session['lista'] = lista_atual
        session.modified = True
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        origens = list({item.get('importacao_tipo', 'manual') for item in lista_atual})
        return render_template(
            "preview.html",
            lista=lista_atual,
            GOOGLE_API_KEY=google_api_key,
            CORES_IMPORTACAO=CORES_IMPORTACAO,
            origens=origens
        )
    except Exception as e:
        logger.error(f"Erro na rota /preview: {str(e)}", exc_info=True)
        return render_template("error.html", msg=str(e)), 400

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()

        if not file or not empresa:
            return jsonify({"success": False, "msg": "Arquivo ou empresa não especificados"}), 400

        if not extensao_permitida(file.filename):
            return jsonify({"success": False, "msg": "Tipo de arquivo não permitido"}), 400

        lista_atual = session.get('lista', [])
        order_start = len(lista_atual)
        if empresa == "delnext":
            file.seek(0)
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(file, header=1)
            else:
                df = pd.read_excel(file, header=1)
            col_end = [c for c in df.columns if 'morada' in c.lower() or 'endereco' in c.lower()]
            col_cep = [c for c in df.columns if 'codigo postal' in c.lower() or 'cod postal' in c.lower() or 'cep' in c.lower() or 'postal' in c.lower()]
            if not col_end or not col_cep:
                return jsonify({"success": False, "msg": "A planilha da Delnext deve conter as colunas 'Morada' e 'Código Postal'!"}), 400
            enderecos = df[col_end[0]].astype(str).tolist()
            ceps = df[col_cep[0]].astype(str).tolist()
            order_numbers = [str(i + 1 + order_start) for i in range(len(enderecos))]
            tipo_import = "delnext"

        elif empresa == "paack":
            file.seek(0)
            if file.filename.lower().endswith('.csv') or file.filename.lower().endswith('.txt'):
                conteudo = file.read().decode("utf-8")
                linhas = conteudo.splitlines()
                regex_cep = re.compile(r'(\d{4}-\d{3})')
                enderecos, ceps, order_numbers = [], [], []
                i = 0
                while i < len(linhas) - 3:
                    endereco_linha = linhas[i].strip()
                    if linhas[i+2].strip() == endereco_linha:
                        order_number = linhas[i+3].strip()
                        cep_match = regex_cep.search(endereco_linha)
                        cep = cep_match.group(1) if cep_match else ""
                        enderecos.append(endereco_linha)
                        ceps.append(cep)
                        order_numbers.append(order_number)
                        i += 4
                    else:
                        i += 1
                tipo_import = "paack"
            else:
                df = pd.read_excel(file, header=0)
                col_end = [c for c in df.columns if 'endereco' in c.lower() or 'address' in c.lower()]
                col_cep = [c for c in df.columns if 'cep' in c.lower() or 'postal' in c.lower()]
                if not col_end or not col_cep:
                    return jsonify({"success": False, "msg": "A planilha deve conter colunas de endereço e CEP!"}), 400
                enderecos = df[col_end[0]].astype(str).tolist()
                ceps = df[col_cep[0]].astype(str).tolist()
                order_numbers = [str(i + 1 + order_start) for i in range(len(enderecos))]
                tipo_import = "paack"
        else:
            return jsonify({"success": False, "msg": "Empresa não suportada para importação!"}), 400

        for endereco, cep, order_number in zip(enderecos, ceps, order_numbers):
            res_google = valida_rua_google(endereco, cep)
            rua_digitada = endereco.split(',')[0] if endereco else ''
            rua_google = res_google.get('route_encontrada', '')
            rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
            cep_ok = cep == res_google.get('postal_code_encontrado', '')
            novo = {
                "order_number": order_number,
                "address": endereco,
                "cep": cep,
                "status_google": res_google.get('status'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "endereco_formatado": res_google.get('endereco_formatado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "rua_google": rua_google,
                "cep_ok": cep_ok,
                "rua_bate": rua_bate,
                "freguesia": res_google.get('sublocality', ''),
                "importacao_tipo": tipo_import,
                "cor": cor_por_tipo(tipo_import)
            }
            if registro_unico(lista_atual, novo):
                lista_atual.append(novo)

        for i, item in enumerate(lista_atual, 1):
            item['order_number'] = i

        session['lista'] = lista_atual
        session.modified = True
        return jsonify({
            "success": True,
            "lista": lista_atual,
            "origens": list({item.get('importacao_tipo', 'manual') for item in lista_atual}),
            "total": len(lista_atual)
        })
    except Exception as e:
        logger.error(f"Erro na importação: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500
# Continuação do routes.py

@main_routes.route('/api/session-data', methods=['GET'])
def get_session_data():
    lista = session.get('lista', [])
    origens = list({item.get("importacao_tipo", "manual") for item in lista})
    return jsonify({
        "success": True,
        "lista": lista,
        "origens": origens,
        "total": len(lista)
    })

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    try:
        data = request.get_json()
        idx = data.get('idx', -1)
        endereco = data.get('endereco', '')
        cep = data.get('cep', '')
        importacao_tipo = data.get('importacao_tipo', 'manual')

        res_google = valida_rua_google(endereco, cep)
        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = res_google.get('route_encontrada', '')
        rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
        cep_ok = cep == res_google.get('postal_code_encontrado', '')

        lista_atual = session.get('lista', [])
        cor = CORES_IMPORTACAO[1] if importacao_tipo == "delnext" else CORES_IMPORTACAO[2] if importacao_tipo == "paack" else CORES_IMPORTACAO[0]

        novo_item = {
            "order_number": data.get('numero_pacote', str(idx+1)),
            "address": endereco,
            "cep": cep,
            "status_google": res_google.get('status'),
            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
            "latitude": res_google.get('coordenadas', {}).get('lat'),
            "longitude": res_google.get('coordenadas', {}).get('lng'),
            "rua_google": rua_google,
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "freguesia": res_google.get('sublocality', ''),
            "importacao_tipo": importacao_tipo,
            "cor": cor
        }
        if 0 <= idx < len(lista_atual):
            lista_atual[idx] = novo_item
        else:
            lista_atual.append(novo_item)

        session['lista'] = lista_atual
        session.modified = True

        return jsonify({
            "success": True,
            "item": novo_item,
            "idx": idx if idx >= 0 else len(lista_atual) - 1
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

@main_routes.route('/generate', methods=['POST'])
def generate():
    try:
        global csv_content
        total = int(request.form['total'])
        lista = []

        for i in range(total):
            item = {
                "order_number": request.form.get(f'numero_pacote_{i}', ''),
                "address": request.form.get(f'endereco_{i}', ''),
                "cep": request.form.get(f'cep_{i}', ''),
                "importacao_tipo": request.form.get(f'importacao_tipo_{i}', 'manual'),
                "cor": request.form.get(f'cor_{i}', CORES_IMPORTACAO[0])
            }
            res_google = valida_rua_google(item["address"], item["cep"])
            item.update({
                "status_google": res_google.get('status'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat'),
                "longitude": res_google.get('coordenadas', {}).get('lng'),
                "rua_google": res_google.get('route_encontrada', ''),
                "cep_ok": item["cep"] == res_google.get('postal_code_encontrado', ''),
                "rua_bate": normalizar(item["address"].split(',')[0]) in normalizar(res_google.get('route_encontrada', '')) if item["address"] else False,
                "freguesia": res_google.get('sublocality', '')
            })
            lista.append(item)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "order number", "name", "address", "latitude", "longitude", "duration",
            "start time", "end time", "phone", "contact", "notes", "color",
            "Group", "rua_google", "freguesia_google", "status"
        ])

        for row in lista:
            status = "Validado"
            if not row["cep_ok"]:
                status = "CEP divergente"
            elif not row["rua_bate"]:
                status = "Rua divergente"
            writer.writerow([
                row["order_number"], "", row["address"],
                row["latitude"], row["longitude"], "", "", "", "", "",
                row["postal_code_encontrado"] or row["cep"],
                row["cor"], "", row["rua_google"],
                row.get("freguesia", ""), status
            ])
        csv_content = output.getvalue()
        return redirect(url_for('main.download'))
    except Exception as e:
        return jsonify({"success": False, "msg": f"Erro ao gerar CSV: {str(e)}"}), 500

@main_routes.route('/download')
def download():
    global csv_content
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )

@main_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        idx = data.get('idx')
        lat = data.get('lat')
        lng = data.get('lng')

        if None in [idx, lat, lng]:
            return jsonify({'success': False, 'msg': 'Dados incompletos'}), 400

        import requests
        api_key = os.environ.get('GOOGLE_API_KEY', '')
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {'latlng': f"{lat},{lng}", 'key': api_key, 'region': 'pt'}
        r = requests.get(url, params=params, timeout=(3.05, 7))
        data = r.json()
        if not data.get('results'):
            return jsonify({'success': False, 'msg': 'Sem resultados do Google'})

        res = data['results'][0]
        address = res['formatted_address']
        postal_code = ''
        for c in res['address_components']:
            if 'postal_code' in c['types']:
                postal_code = c['long_name']
                break

        # Atualiza a sessão
        lista_atual = session.get('lista', [])
        if 0 <= idx < len(lista_atual):
            lista_atual[idx].update({
                "latitude": lat,
                "longitude": lng
            })
            session['lista'] = lista_atual
            session.modified = True

        return jsonify({
            'success': True,
            'address': address,
            'cep': postal_code
        })
    except requests.Timeout:
        return jsonify({'success': False, 'msg': 'Timeout ao conectar com o Google Maps'}), 504
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)}), 500
