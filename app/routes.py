from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
import re
import csv
import io
import os
import pandas as pd
from .utils import valida_rua_google

main_routes = Blueprint('main', __name__)
csv_content = None

def normalizar(texto):
    import unicodedata
    if not texto:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c)
    ).strip()

CORES_IMPORTACAO = [
    "#0074D9",  # Azul - manual
    "#FF851B",  # Laranja - delnext
    "#2ECC40",  # Verde - paack
    "#B10DC9",  # Roxo
    "#FF4136",  # Vermelho
]

@main_routes.route('/', methods=['GET'])
def home():
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    enderecos_brutos = request.form.get('enderecos', '')
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
                    "importacao_tipo": "manual"
                })
                i += 4
            else:
                i += 1
        else:
            i += 1

    # Acumula na sessão sem sobrescrever (adiciona)
    lista_atual = session.get('lista', [])
    if lista_preview:
        lista_final = lista_atual + lista_preview
    else:
        lista_final = lista_atual

    # Gera lista de origens distintas para exibir filtros/badges
    origens = list({item.get('importacao_tipo', 'manual') for item in lista_final})

    session['lista'] = lista_final
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    return render_template(
        "preview.html",
        lista=lista_final,
        GOOGLE_API_KEY=google_api_key,
        CORES_IMPORTACAO=CORES_IMPORTACAO,
        origens=origens
    )

# -------- ROTA DE IMPORTAÇÃO DE PLANILHA XLS/XLSX/CSV --------
@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    file = request.files.get('planilha')
    empresa = request.form.get('empresa', '').lower()
    if not file or not empresa:
        return "Arquivo ou empresa não especificados", 400

    if empresa == "delnext":
        file.seek(0)
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file, header=1)
        else:
            df = pd.read_excel(file, header=1)
        col_end = [c for c in df.columns if 'morada' in c.lower() or 'endereco' in c.lower()]
        col_cep = [c for c in df.columns if 'codigo postal' in c.lower() or 'cod postal' in c.lower() or 'cep' in c.lower() or 'postal' in c.lower()]
        if not col_end or not col_cep:
            return "A planilha da Delnext deve conter as colunas 'Morada' e 'Código Postal'!", 400
        enderecos = df[col_end[0]].astype(str).tolist()
        ceps = df[col_cep[0]].astype(str).tolist()
        tipo_import = "delnext"
    elif empresa == "paack":
        file.seek(0)
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file, header=0)
        else:
            df = pd.read_excel(file, header=0)
        col_end = [c for c in df.columns if 'endereco' in c.lower() or 'address' in c.lower()]
        col_cep = [c for c in df.columns if 'cep' in c.lower() or 'postal' in c.lower()]
        if not col_end or not col_cep:
            return "A planilha deve conter colunas de endereço e CEP!", 400
        enderecos = df[col_end[0]].astype(str).tolist()
        ceps = df[col_cep[0]].astype(str).tolist()
        tipo_import = "paack"
    else:
        return "Empresa não suportada para importação!", 400

    # NÃO ACUMULAR lista, zere sempre ao importar planilha!
    lista_nova = []
    for idx, (endereco, cep) in enumerate(zip(enderecos, ceps)):
        res_google = valida_rua_google(endereco, cep)
        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = res_google.get('route_encontrada', '')
        rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
        cep_ok = cep == res_google.get('postal_code_encontrado', '')
        lista_nova.append({
            "order_number": idx + 1,
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
            "importacao_tipo": tipo_import
        })

    origens = list({item.get('importacao_tipo', 'manual') for item in lista_nova})
    session['lista'] = lista_nova
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    return render_template(
        "preview.html",
        lista=lista_nova,
        GOOGLE_API_KEY=google_api_key,
        CORES_IMPORTACAO=CORES_IMPORTACAO,
        origens=origens
    )
# -------- FIM DA ROTA DE IMPORTAÇÃO --------

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    endereco = request.form.get('endereco')
    cep = request.form.get('cep')
    numero_pacote = request.form.get('numero_pacote')
    res_google = valida_rua_google(endereco, cep)
    rua_digitada = endereco.split(',')[0] if endereco else ''
    rua_google = res_google.get('route_encontrada', '')
    rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
    cep_ok = cep == res_google.get('postal_code_encontrado', '')
    return jsonify({
        'order_number': numero_pacote,
        'address': endereco,
        'cep': cep,
        'status_google': res_google.get('status'),
        'postal_code_encontrado': res_google.get('postal_code_encontrado', ''),
        'endereco_formatado': res_google.get('endereco_formatado', ''),
        'latitude': res_google.get('coordenadas', {}).get('lat', ''),
        'longitude': res_google.get('coordenadas', {}).get('lng', ''),
        'rua_google': rua_google,
        'cep_ok': cep_ok,
        'rua_bate': rua_bate,
        'freguesia_google': res_google.get('sublocality', ''),
    })

@main_routes.route('/generate', methods=['POST'])
def generate():
    global csv_content
    total = int(request.form['total'])
    lista = []
    for i in range(total):
        numero_pacote = request.form.get(f'numero_pacote_{i}', '')
        endereco = request.form.get(f'endereco_{i}', '')
        cep = request.form.get(f'cep_{i}', '')
        res_google = valida_rua_google(endereco, cep)
        postal_code_encontrado = res_google.get('postal_code_encontrado', '')
        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = res_google.get('route_encontrada', '')
        rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
        cep_ok = cep == postal_code_encontrado
        lista.append({
            "order_number": numero_pacote,
            "address": endereco,
            "cep": cep,
            "status_google": res_google.get('status'),
            "postal_code_encontrado": postal_code_encontrado,
            "latitude": res_google.get('coordenadas', {}).get('lat', ''),
            "longitude": res_google.get('coordenadas', {}).get('lng', ''),
            "rua_google": rua_google,
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "freguesia": res_google.get('sublocality', ''),
        })
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "order number", "name", "address", "latitude", "longitude", "duration", "start time",
        "end time", "phone", "contact", "notes", "color", "Group", "rua_google", "freguesia_google", "status"
    ])
    for row in lista:
        aviso = ""
        if not row["cep_ok"]:
            aviso = "CEP divergente"
        elif not row["rua_bate"]:
            aviso = "Rua divergente"
        else:
            aviso = "Validado"
        writer.writerow([
            row["order_number"], "", row["address"], row["latitude"], row["longitude"], "", "", "", "", "",
            row["postal_code_encontrado"] or row["cep"], "", "", row["rua_google"], row.get("freguesia", ""), aviso
        ])
    csv_content = output.getvalue()
    return redirect(url_for('main.download'))

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
    idx = int(request.form.get('idx'))
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    if not lat or not lng:
        return jsonify({'sucesso': False}), 400
    import requests
    api_key = os.environ.get('GOOGLE_API_KEY', '')
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'latlng': f"{lat},{lng}", 'key': api_key, 'region': 'pt'}
    r = requests.get(url, params=params, timeout=7)
    data = r.json()
    if not data.get('results'):
        return jsonify({'sucesso': False})
    res = data['results'][0]
    address = res['formatted_address']
    postal_code = ''
    for c in res['address_components']:
        if 'postal_code' in c['types']:
            postal_code = c['long_name']
            break
    return jsonify({
        'sucesso': True,
        'address': address,
        'cep': postal_code
    })
