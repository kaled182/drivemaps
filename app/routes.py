from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
import re
import csv
import io
import os
import pandas as pd
import logging
import requests
from functools import lru_cache
import hashlib
from .utils import valida_rua_google

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main_routes = Blueprint('main', __name__)
csv_content = None

# Configurações
EXTENSOES_PERMITIDAS = {'csv', 'xls', 'xlsx', 'txt'}
TAMANHO_MAXIMO = 5 * 1024 * 1024  # 5MB

CORES_IMPORTACAO = [
    "#0074D9",  # Azul - manual
    "#FF851B",  # Laranja - delnext
    "#2ECC40",  # Verde - paack
]

# --- Funções Auxiliares ---
def extensao_permitida(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS

def arquivo_seguro(file):
    return file and file.filename != '' and extensao_permitida(file.filename)

def normalizar(texto):
    import unicodedata
    if not texto: return ''
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c)).strip()

def cor_por_tipo(tipo):
    return {"delnext": CORES_IMPORTACAO[1], "paack": CORES_IMPORTACAO[2]}.get(tipo, CORES_IMPORTACAO[0])

def registro_unico(lista, novo):
    return not any(
        normalizar(item.get("address", "")) == normalizar(novo.get("address", "")) and
        normalizar(item.get("cep", "")) == normalizar(novo.get("cep", "")) and
        item.get("importacao_tipo") == novo.get("importacao_tipo")
        for item in lista
    )

@lru_cache(maxsize=1000)
def valida_rua_google_cache(endereco, cep):
    return valida_rua_google(endereco, cep)

# --- Rotas Principais ---
@main_routes.route('/', methods=['GET', 'POST'])
def home_or_preview():
    if request.method == 'POST':
        session.clear()
        enderecos_brutos = request.form.get('enderecos', '')
        # Aqui você pode adicionar a lógica de processamento do texto bruto se ainda for necessária
        # Por simplicidade, vamos focar no fluxo de upload que é mais robusto
        lista_inicial = [] # Processar enderecos_brutos para preencher esta lista
        session['lista'] = lista_inicial
    else: # GET request
        session.clear()
        session['lista'] = []

    return render_template(
        "preview.html",
        lista=session.get('lista', []),
        GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", "")
    )

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        if request.content_length > TAMANHO_MAXIMO:
            return jsonify({"success": False, "msg": "Arquivo muito grande (máx. 5MB)."}), 400

        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()

        if not arquivo_seguro(file) or not empresa:
            return jsonify({"success": False, "msg": "Arquivo ou empresa inválidos."}), 400

        lista_existente = session.get('lista', [])
        lista_atual = [item for item in lista_existente if item.get('importacao_tipo') != empresa]

        # Leitura do arquivo
        df = None
        try:
            header_row = 1 if empresa == 'delnext' else 0
            if file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file, header=header_row)
            else: # .csv, .txt
                df = pd.read_csv(file, header=header_row, sep=None, engine='python', encoding='utf-8')
        except Exception as e:
            return jsonify({"success": False, "msg": f"Não foi possível ler o arquivo. Verifique o formato. Erro: {e}"}), 400

        if df.empty:
            return jsonify({"success": False, "msg": "A planilha está vazia."}), 400

        # Mapeamento de colunas flexível
        df.columns = [str(c).lower() for c in df.columns]
        nomes_col_end = ['endereco', 'morada', 'address']
        nomes_col_cep = ['cep', 'código postal', 'codigo postal', 'postal_code']
        
        col_end = next((c for c in df.columns if c in nomes_col_end), None)
        col_cep = next((c for c in df.columns if c in nomes_col_cep), None)

        if not col_end or not col_cep:
            return jsonify({"success": False, "msg": f"Colunas de endereço/CEP não encontradas. Verifique os cabeçalhos do arquivo."}), 400

        # Processamento das linhas
        novos_itens_importados = []
        for _, row in df.iterrows():
            endereco = str(row[col_end]).strip()
            cep = str(row[col_cep]).strip()
            if not endereco or not cep: continue

            cep = re.sub(r'[^\d-]', '', cep)
            if len(cep) == 7 and '-' not in cep: cep = f"{cep[:4]}-{cep[4:]}"
            if len(cep) == 8 and '-' not in cep: cep = f"{cep[:4]}-{cep[4:]}"

            res_google = valida_rua_google_cache(endereco, cep)
            
            novo = {
                "order_number": "", "address": endereco, "cep": cep,
                "status_google": res_google.get('status', 'NÃO VALIDADO'),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "importacao_tipo": empresa, "cor": cor_por_tipo(empresa),
                # ... outros campos derivados de res_google
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "endereco_formatado": res_google.get('endereco_formatado', ''),
                "rua_google": res_google.get('route_encontrada', ''),
                "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                "rua_bate": (normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', ''))),
                "freguesia": res_google.get('sublocality', '')
            }
            if registro_unico(lista_atual + novos_itens_importados, novo):
                novos_itens_importados.append(novo)

        lista_atual.extend(novos_itens_importados)
        # ... (lógica de reindexação, se necessário) ...
        session['lista'] = lista_atual
        session.modified = True
        
        return jsonify({"success": True, "lista": lista_atual})

    except Exception as e:
        logger.error(f"Erro na importação: {e}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro inesperado no servidor."}), 500

# ... O resto das rotas (/api/validar-linha, /api/add-address, etc.) continua igual à última versão que enviei ...
# Para garantir, aqui estão elas completas:

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    try:
        data = request.get_json()
        idx = int(data.get('idx', -1))
        endereco = data.get('endereco', '')
        cep = data.get('cep', '')

        lista_atual = session.get('lista', [])
        if not (0 <= idx < len(lista_atual)):
            return jsonify({"success": False, "msg": "Índice inválido."}), 400

        item_original = lista_atual[idx]
        item_original['address'] = endereco
        item_original['cep'] = cep
        
        res_google = valida_rua_google_cache(endereco, cep)
        rua_digitada = endereco.split(',')[0]
        rua_google = res_google.get('route_encontrada', '')

        item_original.update({
            "status_google": res_google.get('status', 'ERRO'),
            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
            "endereco_formatado": res_google.get('endereco_formatado', ''),
            "latitude": res_google.get('coordenadas', {}).get('lat', ''),
            "longitude": res_google.get('coordenadas', {}).get('lng', ''),
            "rua_google": rua_google,
            "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
            "rua_bate": (normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)),
            "freguesia": res_google.get('sublocality', '')
        })

        session['lista'] = lista_atual
        session.modified = True
        
        return jsonify({"success": True, "item": item_original})
    except Exception as e:
        logger.error(f"Erro na validação de linha: {e}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro no servidor: {e}"}), 500

@main_routes.route('/api/add-address', methods=['POST'])
def add_address():
    try:
        lista_atual = session.get('lista', [])
        
        counters = {'manual': 0}
        for item in lista_atual:
            if item.get('importacao_tipo') == 'manual' and str(item.get('order_number')).isdigit():
                counters['manual'] = max(counters['manual'], int(item.get('order_number')))
        
        novo_num = counters['manual'] + 1
        novo_item = {
            "order_number": str(novo_num), "address": "", "cep": "", 
            "status_google": "NÃO VALIDADO", "postal_code_encontrado": "", "endereco_formatado": "",
            "latitude": "", "longitude": "", "rua_google": "",
            "cep_ok": False, "rua_bate": False, "freguesia": "",
            "importacao_tipo": "manual", "cor": cor_por_tipo("manual")
        }

        lista_atual.append(novo_item)
        session['lista'] = lista_atual
        session.modified = True
        return jsonify({"success": True, "item": novo_item, "idx": len(lista_atual) - 1})
    except Exception as e:
        logger.error(f"Erro ao adicionar endereço: {e}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro no servidor: {e}"}), 500

@main_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        idx, lat, lng = data.get('idx'), data.get('lat'), data.get('lng')

        if None in [idx, lat, lng]:
            return jsonify({'success': False, 'msg': 'Dados incompletos.'}), 400
        
        lista_atual = session.get('lista', [])
        if not (0 <= int(idx) < len(lista_atual)):
            return jsonify({"success": False, "msg": "Índice inválido."}), 400

        api_key = os.environ.get('GOOGLE_API_KEY', '')
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={'latlng': f"{lat},{lng}", 'key': api_key, 'region': 'pt', 'language': 'pt-PT'}
        )
        response.raise_for_status()
        geocode_data = response.json()

        if not geocode_data.get('results'):
            return jsonify({'success': False, 'msg': 'Endereço não encontrado.'})

        result = geocode_data['results'][0]
        address = result['formatted_address']
        postal_code = next((c['long_name'] for c in result['address_components'] if 'postal_code' in c['types']), '')
        
        item_atualizado = lista_atual[int(idx)]
        item_atualizado.update({
            "latitude": lat, "longitude": lng, "address": address, "cep": postal_code,
            "status_google": "OK", "postal_code_encontrado": postal_code, "endereco_formatado": address, 
            "cep_ok": True, "rua_bate": True
        })
        session['lista'] = lista_atual
        session.modified = True
        return jsonify({'success': True, 'item': item_atualizado})
    except Exception as e:
        logger.error(f"Erro no reverse-geocode: {e}", exc_info=True)
        return jsonify({'success': False, 'msg': str(e)}), 500

@main_routes.route('/generate', methods=['POST'])
def generate():
    # ... (código para gerar CSV)
    global csv_content
    lista_para_csv = session.get('lista', [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order number", "address", "latitude", "longitude", "notes", "color", "status"])
    for row in lista_para_csv:
        status = "Validado"
        if not row.get("cep_ok"): status = "CEP divergente"
        elif not row.get("rua_bate"): status = "Rua divergente"
        writer.writerow([row.get(k, "") for k in ["order_number", "address", "latitude", "longitude"]] + [row.get("postal_code_encontrado", "") or row.get("cep", ""), row.get("cor", ""), status])
    csv_content = output.getvalue()
    return redirect(url_for('main.download'))

@main_routes.route('/download')
def download():
    # ... (código para download do CSV)
    global csv_content
    if not csv_content: return redirect(url_for('main.home_or_preview'))
    buffer = io.BytesIO(csv_content.encode("utf-8-sig")) # Usar utf-8-sig para melhor compatibilidade com Excel
    csv_content = None
    return send_file(buffer, mimetype='text/csv', as_attachment=True, download_name="enderecos_myway.csv")
