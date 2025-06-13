from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
import re
import csv
import io
import os
import pandas as pd
from .utils import valida_rua_google
from random import randint

main_routes = Blueprint('main', __name__)
csv_content = None

# Paleta de cores para diferentes importações (azul escuro como padrão)
CORES_IMPORTACAO = [
    '#001F3F',  # Azul muito escuro (padrão)
    '#0074D9',  # Azul
    '#7FDBFF',  # Azul claro
    '#39CCCC',  # Ciano
    '#3D9970',  # Verde oliva
    '#2ECC40',  # Verde
    '#FFDC00'   # Amarelo
]

def normalizar(texto):
    """Normaliza texto para comparação removendo acentos e espaços."""
    import unicodedata
    if not texto:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto.lower()) 
        if not unicodedata.combining(c)
    ).strip()

@main_routes.route('/', methods=['GET'])
def home():
    """Rota principal que limpa a sessão e exibe o formulário."""
    session.clear()
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    """Processa endereços digitados manualmente."""
    enderecos_brutos = request.form['enderecos']
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
    lista_preview = []
    
    # Gera um ID de cor para esta importação
    importacao_id = randint(0, len(CORES_IMPORTACAO)-1)
    
    i = 0
    while i < len(linhas) - 2:
        linha = linhas[i]
        cep_match = regex_cep.search(linha)
        if cep_match:
            if i + 2 < len(linhas) and linhas[i+2] == linha:
                numero_pacote = linhas[i+3] if (i+3) < len(linhas) else ""
                cep = cep_match.group(1)
                res_google = valida_rua_google(linha, cep)
                
                # Validações
                rua_digitada = linha.split(',')[0] if linha else ''
                rua_google = res_google.get('route_encontrada', '')
                rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
                cep_ok = cep == res_google.get('postal_code_encontrado', '')
                
                lista_preview.append({
                    "order_number": "",  # Será preenchido depois
                    "address": linha,
                    "cep": cep,
                    "status_google": res_google.get('status'),
                    "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                    "endereco_formatado": res_google.get('endereco_formatado', ''),
                    "latitude": res_google.get('coordenadas', {}).get('lat'),
                    "longitude": res_google.get('coordenadas', {}).get('lng'),
                    "rua_google": rua_google,
                    "cep_ok": cep_ok,
                    "rua_bate": rua_bate,
                    "freguesia": res_google.get('sublocality', ''),
                    "importacao_id": importacao_id,
                    "importacao_tipo": "manual",
                    "cor": CORES_IMPORTACAO[importacao_id]
                })
                i += 4
            else:
                i += 1
        else:
            i += 1

    # Mescla com a lista existente na sessão
    lista_atual = session.get('lista', [])
    lista_final = lista_atual + lista_preview

    # Reindexa todos os IDs
    for i, item in enumerate(lista_final, 1):
        item['order_number'] = i

    session['lista'] = lista_final
    return render_template(
        "preview.html", 
        lista=lista_final, 
        GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", "")
    )

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    """Processa arquivos de planilha de diferentes empresas."""
    file = request.files.get('planilha')
    empresa = request.form.get('empresa', '').lower()
    
    if not file or not empresa:
        return "Arquivo ou empresa não especificados", 400

    # Gera um ID de cor para esta importação
    importacao_id = randint(0, len(CORES_IMPORTACAO)-1)
    
    try:
        # Processamento específico por empresa
        if empresa == "delnext":
            file.seek(0)
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(file, header=1)
            else:
                df = pd.read_excel(file, header=1)
            
            # Encontra colunas automaticamente
            col_end = next((c for c in df.columns if 'morada' in c.lower() or 'endereco' in c.lower()), None)
            col_cep = next((c for c in df.columns if 'codigo postal' in c.lower() or 'cod postal' in c.lower() or 'cep' in c.lower()), None)
            
            if not col_end or not col_cep:
                return "A planilha deve conter colunas de endereço e CEP!", 400
                
            enderecos = df[col_end].astype(str).tolist()
            ceps = df[col_cep].astype(str).str.extract(r'(\d{4}-\d{3})')[0].tolist()
            
        elif empresa == "paack":
            file.seek(0)
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(file, header=0)
            else:
                df = pd.read_excel(file, header=0)
                
            col_end = next((c for c in df.columns if 'endereco' in c.lower() or 'address' in c.lower()), None)
            col_cep = next((c for c in df.columns if 'cep' in c.lower() or 'postal' in c.lower()), None)
            
            if not col_end or not col_cep:
                return "A planilha deve conter colunas de endereço e CEP!", 400
                
            enderecos = df[col_end].astype(str).tolist()
            ceps = df[col_cep].astype(str).str.extract(r'(\d{4}-\d{3})')[0].tolist()
            
        else:
            return "Empresa não suportada para importação!", 400

        # Processa cada endereço
        lista_atual = session.get('lista', [])
        novos = []
        
        for endereco, cep in zip(enderecos, ceps):
            if not endereco or not cep or pd.isna(endereco) or pd.isna(cep):
                continue
                
            res_google = valida_rua_google(endereco, cep)
            rua_digitada = endereco.split(',')[0] if endereco else ''
            rua_google = res_google.get('route_encontrada', '')
            
            novos.append({
                "order_number": "",
                "address": endereco,
                "cep": cep,
                "status_google": res_google.get('status'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "endereco_formatado": res_google.get('endereco_formatado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat'),
                "longitude": res_google.get('coordenadas', {}).get('lng'),
                "rua_google": rua_google,
                "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                "rua_bate": normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada),
                "freguesia": res_google.get('sublocality', ''),
                "importacao_id": importacao_id,
                "importacao_tipo": empresa,
                "cor": CORES_IMPORTACAO[importacao_id]
            })

        # Combina com a lista existente
        lista_final = lista_atual + novos

        # Reindexa todos os order_numbers
        for i, item in enumerate(lista_final, 1):
            item['order_number'] = i

        session['lista'] = lista_final
        return render_template(
            "preview.html", 
            lista=lista_final, 
            GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", "")
        )

    except Exception as e:
        return f"Erro ao processar arquivo: {str(e)}", 500

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    """Valida um endereço individual via AJAX."""
    endereco = request.form.get('endereco')
    cep = request.form.get('cep')
    numero_pacote = request.form.get('numero_pacote')
    
    if not endereco or not cep:
        return jsonify({"error": "Endereço e CEP são obrigatórios"}), 400
    
    res_google = valida_rua_google(endereco, cep)
    rua_digitada = endereco.split(',')[0] if endereco else ''
    rua_google = res_google.get('route_encontrada', '')
    
    return jsonify({
        'order_number': numero_pacote,
        'address': endereco,
        'cep': cep,
        'status_google': res_google.get('status'),
        'postal_code_encontrado': res_google.get('postal_code_encontrado', ''),
        'endereco_formatado': res_google.get('endereco_formatado', ''),
        'latitude': res_google.get('coordenadas', {}).get('lat'),
        'longitude': res_google.get('coordenadas', {}).get('lng'),
        'rua_google': rua_google,
        'cep_ok': cep == res_google.get('postal_code_encontrado', ''),
        'rua_bate': normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada),
        'freguesia_google': res_google.get('sublocality', ''),
        # Mantém os dados de importação originais
        'importacao_id': request.form.get('importacao_id', 0),
        'importacao_tipo': request.form.get('importacao_tipo', 'manual'),
        'cor': request.form.get('cor', CORES_IMPORTACAO[0])
    })

@main_routes.route('/generate', methods=['POST'])
def generate():
    """Gera o arquivo CSV final."""
    global csv_content
    total = int(request.form['total'])
    lista = []
    
    for i in range(total):
        numero_pacote = request.form.get(f'numero_pacote_{i}', '')
        endereco = request.form.get(f'endereco_{i}', '')
        cep = request.form.get(f'cep_{i}', '')
        
        if not endereco or not cep:
            continue
            
        res_google = valida_rua_google(endereco, cep)
        postal_code = res_google.get('postal_code_encontrado', '')
        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = res_google.get('route_encontrada', '')
        
        lista.append({
            "order_number": numero_pacote,
            "address": endereco,
            "cep": cep,
            "postal_code_encontrado": postal_code,
            "latitude": res_google.get('coordenadas', {}).get('lat'),
            "longitude": res_google.get('coordenadas', {}).get('lng'),
            "rua_google": rua_google,
            "status": "OK" if cep == postal_code and normalizar(rua_digitada) in normalizar(rua_google) else "AVISO",
            "freguesia": res_google.get('sublocality', '')
        })

    # Gera o CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "order number", "name", "address", "latitude", "longitude", 
        "duration", "start time", "end time", "phone", "contact", 
        "notes", "color", "Group", "rua_google", "freguesia", "status"
    ])
    
    for row in lista:
        writer.writerow([
            row["order_number"], "", row["address"], 
            row["latitude"], row["longitude"], "", "", 
            "", "", "", row["postal_code_encontrado"] or row["cep"], 
            "", "", row["rua_google"], row["freguesia"], row["status"]
        ])
    
    csv_content = output.getvalue()
    return redirect(url_for('main.download'))

@main_routes.route('/download')
def download():
    """Fornece o arquivo CSV para download."""
    global csv_content
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )

@main_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    """Converte coordenadas em endereço (para arrastar marcadores)."""
    idx = request.form.get('idx')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    
    if not all([idx, lat, lng]):
        return jsonify({'sucesso': False}), 400
        
    try:
        import requests
        api_key = os.environ.get('GOOGLE_API_KEY', '')
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{lat},{lng}", 
            'key': api_key, 
            'region': 'pt',
            'language': 'pt'
        }
        
        response = requests.get(url, params=params, timeout=7)
        data = response.json()
        
        if not data.get('results'):
            return jsonify({'sucesso': False})
            
        result = data['results'][0]
        address = result['formatted_address']
        postal_code = next(
            (c['long_name'] for c in result['address_components'] 
            if 'postal_code' in c['types']),
            ''
        )
        
        return jsonify({
            'sucesso': True,
            'address': address,
            'cep': postal_code
        })
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
