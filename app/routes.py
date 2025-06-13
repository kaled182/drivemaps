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

def registro_unico(lista, novo):
    """Impede duplicidade de endereço + cep + tipo de importação."""
    for item in lista:
        if (
            normalizar(item["address"]) == normalizar(novo["address"]) and
            normalizar(item["cep"]) == normalizar(novo["cep"]) and
            item.get("importacao_tipo") == novo.get("importacao_tipo")
        ):
            return False
    return True

@main_routes.route('/', methods=['GET'])
def home():
    # Limpa completamente a sessão ao entrar na home
    session.clear()
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    enderecos_brutos = request.form.get('enderecos', '')
    if not enderecos_brutos.strip():
        return redirect(url_for('main.home'))
    
    # Limpa a lista apenas se for uma nova importação manual
    session['lista'] = []
    
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
                    "cor": CORES_IMPORTACAO[0]
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

    origens = list({item.get('importacao_tipo', 'manual') for item in lista_atual})

    for i, item in enumerate(lista_atual, 1):
        item['order_number'] = i

    session['lista'] = lista_atual
    session.modified = True
    
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    return render_template(
        "preview.html",
        lista=lista_atual,
        GOOGLE_API_KEY=google_api_key,
        CORES_IMPORTACAO=CORES_IMPORTACAO,
        origens=origens
    )

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    file = request.files.get('planilha')
    empresa = request.form.get('empresa', '').lower()
    if not file or not empresa:
        return "Arquivo ou empresa não especificados", 400

    # Mantém a lista existente na sessão para acumular
    lista_atual = session.get('lista', [])

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
        order_numbers = [str(i+1+len(lista_atual)) for i in range(len(enderecos))]
        tipo_import = "delnext"
        cor = CORES_IMPORTACAO[1]

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
            cor = CORES_IMPORTACAO[2]
        else:
            df = pd.read_excel(file, header=0)
            col_end = [c for c in df.columns if 'endereco' in c.lower() or 'address' in c.lower()]
            col_cep = [c for c in df.columns if 'cep' in c.lower() or 'postal' in c.lower()]
            if not col_end or not col_cep:
                return "A planilha deve conter colunas de endereço e CEP!", 400
            enderecos = df[col_end[0]].astype(str).tolist()
            ceps = df[col_cep[0]].astype(str).tolist()
            order_numbers = [str(i+1+len(lista_atual)) for i in range(len(enderecos))]
            tipo_import = "paack"
            cor = CORES_IMPORTACAO[2]
    else:
        return "Empresa não suportada para importação!", 400

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
            "cor": cor
        }
        if registro_unico(lista_atual, novo):
            lista_atual.append(novo)

    for i, item in enumerate(lista_atual, 1):
        item['order_number'] = i

    origens = list({item.get('importacao_tipo', 'manual') for item in lista_atual})
    session['lista'] = lista_atual
    session.modified = True
    
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    return render_template(
        "preview.html",
        lista=lista_atual,
        GOOGLE_API_KEY=google_api_key,
        CORES_IMPORTACAO=CORES_IMPORTACAO,
        origens=origens
    )

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    endereco = request.form.get('endereco')
    cep = request.form.get('cep')
    numero_pacote = request.form.get('numero_pacote')
    importacao_tipo = request.form.get('importacao_tipo', 'manual')
    idx = int(request.form.get('idx', -1))
    
    res_google = valida_rua_google(endereco, cep)
    rua_digitada = endereco.split(',')[0] if endereco else ''
    rua_google = res_google.get('route_encontrada', '')
    rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
    cep_ok = cep == res_google.get('postal_code_encontrado', '')
    
    # Atualiza a lista na sessão
    lista_atual = session.get('lista', [])
    
    if idx >= 0 and idx < len(lista_atual):
        # Atualiza linha existente
        lista_atual[idx].update({
            "address": endereco,
            "cep": cep,
            "status_google": res_google.get('status'),
            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
            "latitude": res_google.get('coordenadas', {}).get('lat', ''),
            "longitude": res_google.get('coordenadas', {}).get('lng', ''),
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "rua_google": rua_google,
            "freguesia": res_google.get('sublocality', '')
        })
    else:
        # Adiciona nova linha
        cor = CORES_IMPORTACAO[0]  # Cor padrão para manual
        if importacao_tipo == 'delnext':
            cor = CORES_IMPORTACAO[1]
        elif importacao_tipo == 'paack':
            cor = CORES_IMPORTACAO[2]
            
        lista_atual.append({
            "order_number": numero_pacote or str(len(lista_atual) + 1),
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
            "importacao_tipo": importacao_tipo,
            "cor": cor
        })
    
    session['lista'] = lista_atual
    session.modified = True
    
    return jsonify({
        'order_number': numero_pacote or str(len(lista_atual)),
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
        'importacao_tipo': importacao_tipo,
        'cor': lista_atual[-1]['cor']  # Retorna a cor usada
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
        importacao_tipo = request.form.get(f'importacao_tipo_{i}', 'manual')
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
            "importacao_tipo": importacao_tipo
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
        
        # Determina a cor baseada no tipo de importação
        cor = CORES_IMPORTACAO[0]  # Padrão manual
        if row["importacao_tipo"] == "delnext":
            cor = CORES_IMPORTACAO[1]
        elif row["importacao_tipo"] == "paack":
            cor = CORES_IMPORTACAO[2]
            
        writer.writerow([
            row["order_number"], "", row["address"], row["latitude"], row["longitude"], "", "", "", "", "",
            row["postal_code_encontrado"] or row["cep"], cor, "", row["rua_google"], row.get("freguesia", ""), aviso
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
    
    # Atualiza a lista na sessão
    lista_atual = session.get('lista', [])
    if idx >= 0 and idx < len(lista_atual):
        lista_atual[idx]['latitude'] = lat
        lista_atual[idx]['longitude'] = lng
        session['lista'] = lista_atual
        session.modified = True
    
    return jsonify({
        'sucesso': True,
        'address': address,
        'cep': postal_code
    })
