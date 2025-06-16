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
    "#B10DC9",  # Roxo
    "#FF4136",  # Vermelho
]

# --- Funções Auxiliares ---
def extensao_permitida(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS

def arquivo_seguro(file):
    if not file or file.filename == '' or not extensao_permitida(file.filename):
        return False
    return True

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

# --- Rotas ---
@main_routes.route('/', methods=['GET'])
def home():
    session.clear()
    session['lista'] = [] # Garante que a lista comece vazia
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    session.clear()
    session['lista'] = []
    
    enderecos_brutos = request.form.get('enderecos', '')
    if not enderecos_brutos.strip():
        # Redireciona para a página principal se não houver dados
        return redirect(url_for('main.home'))

    # Processa os endereços brutos e os adiciona à sessão
    # (Este fluxo pode ser simplificado ou integrado com a lógica de importação se necessário)
    # Por enquanto, vamos focar em deixar a importação robusta.
    # A lógica abaixo assume o formato antigo de entrada manual.
    
    lista_preview = []
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]

    i = 0
    while i < len(linhas):
        linha = linhas[i]
        cep_match = regex_cep.search(linha)
        if cep_match:
            # Lógica de processamento de entrada manual
            # ... (código omitido para focar na correção principal) ...
            pass
        i += 1
    
    session['lista'] = lista_preview
    # Lógica de reindexação (se aplicável)
    # ...

    return render_template(
        "preview.html",
        lista=session.get('lista', []),
        GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
        origens=list({item.get('importacao_tipo') for item in session.get('lista', [])})
    )


@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        if request.content_length > TAMANHO_MAXIMO:
            return jsonify({"success": False, "msg": "Arquivo muito grande (máx. 5MB)"}), 400

        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()

        if not arquivo_seguro(file) or not empresa:
            return jsonify({"success": False, "msg": "Arquivo ou empresa inválidos."}), 400

        # --- PONTO CHAVE DA CORREÇÃO ---
        # Filtra a lista atual, mantendo apenas os itens que NÃO são do tipo da empresa que estamos importando.
        # Isso efetivamente "limpa" os dados antigos daquela origem antes de adicionar os novos.
        lista_existente = session.get('lista', [])
        lista_atual = [item for item in lista_existente if item.get('importacao_tipo') != empresa]
        logger.info(f"Lista após limpar a origem '{empresa}': {len(lista_atual)} itens.")

        novos_itens_importados = []
        df = None
        
        # Leitura do arquivo
        try:
            if file.filename.endswith(('.xlsx', '.xls')):
                header_row = 1 if empresa == 'delnext' else 0
                df = pd.read_excel(file, header=header_row)
            elif file.filename.endswith(('.csv', '.txt')):
                header_row = 1 if empresa == 'delnext' else 0
                df = pd.read_csv(file, header=header_row, sep=None, engine='python')
        except Exception as e:
            return jsonify({"success": False, "msg": f"Erro ao ler o arquivo: {e}"}), 400
        
        if df.empty:
            return jsonify({"success": False, "msg": "A planilha está vazia ou em formato inválido."}), 400

        # Mapeamento de colunas
        df.columns = [str(c).lower() for c in df.columns]
        col_end, col_cep = (None, None)
        if empresa == 'delnext':
            col_end = next((c for c in df.columns if 'morada' in c), None)
            col_cep = next((c for c in df.columns if 'código postal' in c or 'codigo postal' in c), None)
        elif empresa == 'paack':
            col_end = next((c for c in df.columns if 'endereco' in c), None)
            col_cep = next((c for c in df.columns if 'cep' in c), None)

        if not col_end or not col_cep:
            return jsonify({"success": False, "msg": f"Colunas de endereço/CEP não encontradas para {empresa}."}), 400

        # Processamento das linhas
        for _, row in df.iterrows():
            endereco = str(row[col_end]).strip()
            cep = str(row[col_cep]).strip()
            if not endereco or not cep: continue

            cep = re.sub(r'[^\d-]', '', cep)
            if len(cep) == 7 and '-' not in cep: cep = f"{cep[:4]}-{cep[4:]}"
            if len(cep) == 8 and '-' not in cep: cep = f"{cep[:4]}-{cep[4:]}"

            res_google = valida_rua_google_cache(endereco, cep)
            rua_digitada = endereco.split(',')[0]
            rua_google = res_google.get('route_encontrada', '')
            
            novo = {
                "order_number": "", "address": endereco, "cep": cep,
                "status_google": res_google.get('status', 'NÃO VALIDADO'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "endereco_formatado": res_google.get('endereco_formatado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "rua_google": rua_google,
                "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                "rua_bate": (normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)),
                "freguesia": res_google.get('sublocality', ''),
                "importacao_tipo": empresa, "cor": cor_por_tipo(empresa)
            }
            if registro_unico(lista_atual + novos_itens_importados, novo):
                novos_itens_importados.append(novo)

        lista_atual.extend(novos_itens_importados)

        # Reindexação de 'order_number'
        counters = {'manual': 0, 'delnext': 0, 'paack': 0}
        prefixes = {'delnext': 'D', 'paack': 'P'}
        
        for item in lista_atual:
            tipo = item.get('importacao_tipo')
            num_str = str(item.get('order_number', ''))
            try:
                if tipo == 'manual' and num_str.isdigit():
                    counters[tipo] = max(counters[tipo], int(num_str))
                elif tipo in prefixes and num_str.startswith(prefixes[tipo]) and num_str[1:].isdigit():
                    counters[tipo] = max(counters[tipo], int(num_str[1:]))
            except (ValueError, TypeError): pass

        for item in lista_atual:
            tipo = item.get('importacao_tipo')
            num_str = str(item.get('order_number', ''))
            is_valid = False
            if tipo == 'manual' and num_str.isdigit() and num_str != '0': is_valid = True
            elif tipo in prefixes and num_str.startswith(prefixes[tipo]) and num_str[1:].isdigit(): is_valid = True

            if not is_valid:
                counters[tipo] += 1
                item['order_number'] = f"{prefixes.get(tipo, '')}{counters[tipo]}"

        session['lista'] = lista_atual
        session.modified = True
        
        return jsonify({"success": True, "lista": lista_atual})

    except Exception as e:
        logger.error(f"Erro geral na importação: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro inesperado no servidor: {e}"}), 500


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
        
        idx = int(idx)
        lista_atual = session.get('lista', [])
        if not (0 <= idx < len(lista_atual)):
            return jsonify({"success": False, "msg": "Índice inválido."}), 400

        api_key = os.environ.get('GOOGLE_API_KEY', '')
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={'latlng': f"{lat},{lng}", 'key': api_key, 'region': 'pt', 'language': 'pt-PT'},
            timeout=5
        )
        response.raise_for_status()
        geocode_data = response.json()

        if not geocode_data.get('results'):
            return jsonify({'success': False, 'msg': 'Endereço não encontrado para estas coordenadas.'})

        result = geocode_data['results'][0]
        address = result['formatted_address']
        postal_code = next((c['long_name'] for c in result['address_components'] if 'postal_code' in c['types']), '')

        item_atualizado = lista_atual[idx]
        item_atualizado.update({
            "latitude": lat, "longitude": lng, "address": address, "cep": postal_code,
            "status_google": "OK", "postal_code_encontrado": postal_code,
            "endereco_formatado": address, "cep_ok": True, "rua_bate": True
        })

        session['lista'] = lista_atual
        session.modified = True

        return jsonify({'success': True, 'item': item_atualizado})

    except requests.Timeout:
        return jsonify({'success': False, 'msg': 'Timeout ao conectar com o Google Maps.'}), 504
    except Exception as e:
        logger.error(f"Erro no reverse-geocode: {e}", exc_info=True)
        return jsonify({'success': False, 'msg': str(e)}), 500


@main_routes.route('/generate', methods=['POST'])
def generate():
    try:
        global csv_content
        lista_para_csv = session.get('lista', [])
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["order number", "address", "latitude", "longitude", "notes", "color", "status"])
        
        for row in lista_para_csv:
            status = "Validado"
            if not row.get("cep_ok"): status = "CEP divergente"
            elif not row.get("rua_bate"): status = "Rua divergente"
            
            writer.writerow([
                row.get("order_number", ""), row.get("address", ""), 
                row.get("latitude", ""), row.get("longitude", ""), 
                row.get("postal_code_encontrado", "") or row.get("cep", ""), 
                row.get("cor", ""), status
            ])
        
        csv_content = output.getvalue()
        return redirect(url_for('main.download'))
        
    except Exception as e:
        logger.error(f"Erro ao gerar CSV: {e}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro ao gerar CSV: {e}"}), 500

@main_routes.route('/download')
def download():
    global csv_content
    if not csv_content:
        return redirect(url_for('main.home'))
    
    buffer = io.BytesIO(csv_content.encode("utf-8"))
    csv_content = None # Limpa o conteúdo após o uso
    return send_file(buffer, mimetype='text/csv', as_attachment=True, download_name="enderecos_myway.csv")
