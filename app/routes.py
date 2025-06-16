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
    if file.filename == '':
        return False
    if not extensao_permitida(file.filename):
        return False
    return True

def normalizar(texto):
    import unicodedata
    if not texto:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto.lower())
        if not unicodedata.combining(c)
    ).strip()

def cor_por_tipo(tipo):
    return {
        "delnext": CORES_IMPORTACAO[1],
        "paack": CORES_IMPORTACAO[2]
    }.get(tipo, CORES_IMPORTACAO[0])

def registro_unico(lista, novo):
    """Verifica se um registro (endereço + cep + tipo) já existe na lista para evitar duplicatas."""
    return not any(
        normalizar(item.get("address", "")) == normalizar(novo.get("address", "")) and
        normalizar(item.get("cep", "")) == normalizar(novo.get("cep", "")) and
        item.get("importacao_tipo") == novo.get("importacao_tipo")
        for item in lista
    )

@lru_cache(maxsize=1000)
def valida_rua_google_cache(endereco, cep):
    chave = hashlib.md5(f"{endereco}{cep}".encode()).hexdigest()
    return valida_rua_google(endereco, cep)

# --- Rotas ---
@main_routes.route('/', methods=['GET'])
def home():
    session.clear()
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    try:
        if 'preview_loaded' not in session:
            session.clear()
            session['lista'] = []
            session['preview_loaded'] = True
            session.modified = True

        enderecos_brutos = request.form.get('enderecos', '')
        if not enderecos_brutos.strip():
            raise ValueError("Nenhum endereço fornecido")

        regex_cep = re.compile(r'(\d{4}-\d{3})')
        linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
        lista_preview_novos = [] # Itens a serem adicionados pelo preview

        i = 0
        while i < len(linhas) - 2:
            linha = linhas[i]
            cep_match = regex_cep.search(linha)
            if cep_match:
                if i + 2 < len(linhas) and linhas[i+2] == linha:
                    numero_pacote_str = linhas[i+3] if (i+3) < len(linhas) else ""
                    # Se o numero_pacote_str for um número válido, use-o, senão será vazio e o re-indexador no final irá atribuir.
                    numero_pacote = numero_pacote_str if numero_pacote_str.isdigit() else ""

                    cep = cep_match.group(1)
                    res_google = valida_rua_google_cache(linha, cep)

                    rua_digitada = linha.split(',')[0] if linha else ''
                    rua_google = res_google.get('route_encontrada', '')
                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or
                              normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = cep == res_google.get('postal_code_encontrado', '')

                    novo = {
                        "order_number": numero_pacote, # Pode ser o número digitado ou vazio para re-indexar
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
                    }

                    if registro_unico(session.get('lista', []) + lista_preview_novos, novo): # Verifica duplicidade na lista atual + novos do preview
                        lista_preview_novos.append(novo)
                    i += 4
                else:
                    i += 1
            else:
                i += 1

        lista_atual = session.get('lista', [])
        lista_atual.extend(lista_preview_novos) # Adiciona os novos itens do preview

        # --- Lógica de re-atribuição de order_number para toda a lista ---
        # Este bloco é o mesmo da import_planilha, para garantir consistência.
        manual_counter = 0
        delnext_counter = 0
        paack_counter = 0

        # Encontrar o maior número atual para cada tipo de importação
        for item in lista_atual:
            order_num_str = str(item.get('order_number', ''))
            try:
                if item.get('importacao_tipo') == 'manual' and order_num_str.isdigit():
                    manual_counter = max(manual_counter, int(order_num_str))
                elif item.get('importacao_tipo') == 'delnext' and order_num_str.startswith('D') and order_num_str[1:].isdigit():
                    delnext_counter = max(delnext_counter, int(order_num_str[1:]))
                elif item.get('importacao_tipo') == 'paack' and order_num_str.startswith('P') and order_num_str[1:].isdigit():
                    paack_counter = max(paack_counter, int(order_num_str[1:]))
            except ValueError:
                pass

        # Atribui novos order_numbers
        for item in lista_atual:
            needs_reindex = False
            if item.get('importacao_tipo') == 'manual':
                if not str(item.get('order_number', '')).isdigit(): # Se não é um número simples
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'delnext':
                if not str(item.get('order_number', '')).startswith('D'): # Se não começa com 'D'
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'paack':
                if not str(item.get('order_number', '')).startswith('P'): # Se não começa com 'P'
                    needs_reindex = True

            if needs_reindex:
                if item.get('importacao_tipo') == 'manual':
                    manual_counter += 1
                    item['order_number'] = str(manual_counter)
                elif item.get('importacao_tipo') == 'delnext':
                    delnext_counter += 1
                    item['order_number'] = f"D{delnext_counter}"
                elif item.get('importacao_tipo') == 'paack':
                    paack_counter += 1
                    item['order_number'] = f"P{paack_counter}"

        session['lista'] = lista_atual
        session.modified = True

        return render_template(
            "preview.html",
            lista=lista_atual,
            GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
            CORES_IMPORTACAO=CORES_IMPORTACAO,
            origens=list({item.get('importacao_tipo', 'manual') for item in lista_atual})
        )
    except Exception as e:
        logger.error(f"Erro no preview: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        if request.content_length > TAMANHO_MAXIMO:
            logger.warning(f"Tentativa de upload de arquivo muito grande: {request.content_length} bytes")
            return jsonify({"success": False, "msg": "Arquivo muito grande (máx. 5MB)"}), 400

        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()

        if not file or not empresa:
            logger.warning("Arquivo ou empresa não especificados na importação.")
            return jsonify({"success": False, "msg": "Arquivo ou empresa não especificados"}), 400

        if not arquivo_seguro(file):
            logger.warning(f"Tipo de arquivo não permitido ou inválido: {file.filename}")
            return jsonify({"success": False, "msg": "Tipo de arquivo não permitido ou inválido"}), 400

        lista_atual = session.get('lista', [])
        logger.info(f"Lista atual antes da importação: {len(lista_atual)} itens.")

        try:
            novos_itens_importados = [] # Lista temporária para os novos itens

            if empresa == "delnext":
                file.seek(0)
                filename = file.filename.lower()

                if filename.endswith(('.xlsx', '.xls')):
                    logger.info("Processando arquivo Delnext como Excel.")
                    df = pd.read_excel(file, header=1)
                elif filename.endswith(('.csv', '.txt')):
                    logger.info("Processando arquivo Delnext como CSV/TXT.")
                    try:
                        content = file.read().decode('utf-8')
                        dialect = csv.Sniffer().sniff(content.splitlines()[0], delimiters=[',', ';'])
                        file.seek(0)
                        df = pd.read_csv(io.StringIO(content), header=1, sep=dialect.delimiter)
                    except Exception as csv_err:
                        logger.warning(f"Erro ao tentar detectar separador CSV, tentando padrão: {csv_err}")
                        file.seek(0)
                        df = pd.read_csv(file, header=1, sep=',')
                        if df.empty or ('morada' not in df.columns.str.lower() and 'código postal' not in df.columns.str.lower() and 'codigo postal' not in df.columns.str.lower()):
                            logger.warning("Leitura CSV com vírgula falhou ou colunas não encontradas, tentando ponto e vírgula.")
                            file.seek(0)
                            df = pd.read_csv(file, header=1, sep=';')
                else:
                    return jsonify({
                        "success": False,
                        "msg": "Formato de arquivo Delnext não suportado. Use .xlsx, .xls, .csv ou .txt"
                    }), 400

                if df.empty:
                    return jsonify({
                        "success": False,
                        "msg": "A planilha está vazia ou o formato é inválido após ignorar a primeira linha."
                    }), 400

                df.columns = df.columns.astype(str)

                col_morada = next((c for c in df.columns if 'morada' in c.lower()), None)
                col_cep = next((c for c in df.columns if 'código postal' in c.lower() or 'codigo postal' in c.lower()), None)

                if not col_morada or not col_cep:
                    logger.error(f"Colunas 'Morada' ou 'Código Postal' não encontradas no arquivo Delnext. Colunas disponíveis: {df.columns.tolist()}")
                    return jsonify({
                        "success": False,
                        "msg": "Estrutura inválida. A planilha Delnext deve conter colunas de 'Morada' e 'Código Postal' (ignorando maiúsculas/minúsculas)."
                    }), 400

                last_delnext_order_num = 0
                for item in lista_atual:
                    if item.get('importacao_tipo') == 'delnext' and item.get('order_number', '').startswith('D'):
                        try:
                            num = int(item['order_number'][1:]) # Pega o número após o 'D'
                            if num > last_delnext_order_num:
                                last_delnext_order_num = num
                        except ValueError:
                            continue


                for index, row in df.iterrows():
                    endereco = str(row[col_morada]).strip()
                    cep = str(row[col_cep]).strip()

                    if not endereco or not cep:
                        logger.warning(f"Linha {index+2} (após cabeçalho) ignorada por conter endereço ou CEP vazio: Endereço='{endereco}', CEP='{cep}'")
                        continue

                    cep = re.sub(r'[^\d-]', '', cep)
                    if len(cep) == 8 and '-' not in cep: # Ex: "12345678" vira "1234-567"
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 7 and '-' not in cep: # Ex: "1234567" (se for o caso de faltar um digito mas ter 7)
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 9 and cep.count('-') == 1: # Ex: "1234-5678" Delnext pode vir com 8 digitos
                        cep = cep[:8] # Corta para 1234-567

                    logger.info(f"Processando linha {index+2}: Endereço='{endereco}', CEP formatado='{cep}'")

                    res_google = valida_rua_google_cache(endereco, cep)
                    rua_digitada = endereco.split(',')[0] if endereco else ''
                    rua_google = res_google.get('route_encontrada', '')

                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or
                                  normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = (cep == res_google.get('postal_code_encontrado', ''))

                    novo = {
                        "order_number": "", # Será preenchido após a verificação de duplicidade
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
                        "importacao_tipo": "delnext",
                        "cor": cor_por_tipo("delnext")
                    }

                    if registro_unico(lista_atual, novo):
                        novos_itens_importados.append(novo) # Adiciona à lista temporária
                    else:
                        logger.info(f"Registro duplicado ignorado: {endereco}, {cep}")

            elif empresa == "paack":
                file.seek(0)
                filename = file.filename.lower()

                if filename.endswith(('.xlsx', '.xls')):
                    logger.info("Processando arquivo Paack como Excel.")
                    df = pd.read_excel(file, header=0) # Paack pode ter header=0 ou outro
                elif filename.endswith(('.csv', '.txt')):
                    logger.info("Processando arquivo Paack como CSV/TXT.")
                    try:
                        content = file.read().decode('utf-8')
                        dialect = csv.Sniffer().sniff(content.splitlines()[0], delimiters=[',', ';'])
                        file.seek(0)
                        df = pd.read_csv(io.StringIO(content), header=0, sep=dialect.delimiter)
                    except Exception as csv_err:
                        logger.warning(f"Erro ao tentar detectar separador CSV, tentando padrão para Paack: {csv_err}")
                        file.seek(0)
                        df = pd.read_csv(file, header=0, sep=',')
                        if df.empty or ('endereco' not in df.columns.str.lower() and 'cep' not in df.columns.str.lower()):
                            logger.warning("Leitura CSV Paack com vírgula falhou ou colunas não encontradas, tentando ponto e vírgula.")
                            file.seek(0)
                            df = pd.read_csv(file, header=0, sep=';')
                else:
                     return jsonify({
                        "success": False,
                        "msg": "Formato de arquivo Paack não suportado. Use .xlsx, .xls, .csv ou .txt"
                    }), 400

                if df.empty:
                    return jsonify({
                        "success": False,
                        "msg": "A planilha Paack está vazia ou o formato é inválido."
                    }), 400

                df.columns = df.columns.astype(str)
                col_end = next((c for c in df.columns if 'endereco' in c.lower()), None)
                col_cep = next((c for c in df.columns if 'cep' in c.lower()), None)

                if not col_end or not col_cep:
                    logger.error(f"Colunas 'Endereço' ou 'CEP' não encontradas no arquivo Paack. Colunas disponíveis: {df.columns.tolist()}")
                    return jsonify({"success": False, "msg": "Colunas 'Endereço' e 'CEP' não encontradas na planilha Paack"}), 400

                last_paack_order_num = 0
                for item in lista_atual:
                    if item.get('importacao_tipo') == 'paack' and item.get('order_number', '').startswith('P'):
                        try:
                            num = int(item['order_number'][1:])
                            if num > last_paack_order_num:
                                last_paack_order_num = num
                        except ValueError:
                            continue

                for index, row in df.iterrows():
                    endereco = str(row[col_end]).strip()
                    cep = str(row[col_cep]).strip()

                    if not endereco or not cep:
                        logger.warning(f"Linha {index+1} (Paack) ignorada por conter endereço ou CEP vazio: Endereço='{endereco}', CEP='{cep}'")
                        continue

                    cep = re.sub(r'[^\d-]', '', cep)
                    if len(cep) == 8 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 7 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 9 and cep.count('-') == 1:
                        cep = cep[:8]

                    logger.info(f"Processando linha {index+1} (Paack): Endereço='{endereco}', CEP formatado='{cep}'")

                    res_google = valida_rua_google_cache(endereco, cep)
                    rua_digitada = endereco.split(',')[0] if endereco else ''
                    rua_google = res_google.get('route_encontrada', '')

                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or
                                  normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = (cep == res_google.get('postal_code_encontrado', ''))

                    novo = {
                        "order_number": "", # Será preenchido após a verificação de duplicidade
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
                        "importacao_tipo": "paack",
                        "cor": cor_por_tipo("paack")
                    }

                    if registro_unico(lista_atual, novo):
                        novos_itens_importados.append(novo)
                    else:
                        logger.info(f"Registro duplicado Paack ignorado: {endereco}, {cep}")

            else:
                return jsonify({"success": False, "msg": "Empresa não suportada"}), 400

            # --- Lógica de atribuição de order_number e adição à lista principal ---
            lista_atual.extend(novos_itens_importados)

            manual_counter = 0
            delnext_counter = 0
            paack_counter = 0

            # Encontrar o maior número atual para cada tipo de importação
            for item in lista_atual:
                order_num_str = str(item.get('order_number', ''))
                try:
                    if item.get('importacao_tipo') == 'manual' and order_num_str.isdigit():
                        manual_counter = max(manual_counter, int(order_num_str))
                    elif item.get('importacao_tipo') == 'delnext' and order_num_str.startswith('D') and order_num_str[1:].isdigit():
                        delnext_counter = max(delnext_counter, int(order_num_str[1:]))
                    elif item.get('importacao_tipo') == 'paack' and order_num_str.startswith('P') and order_num_str[1:].isdigit():
                        paack_counter = max(paack_counter, int(order_num_str[1:]))
                except ValueError:
                    pass # Ignora order_numbers mal formatados

            # Atribui novos order_numbers
            for item in lista_atual:
                needs_reindex = False
                if item.get('importacao_tipo') == 'manual':
                    if not str(item.get('order_number', '')).isdigit() or item.get('order_number', '') == "": # Se não é um número simples ou está vazio
                        needs_reindex = True
                elif item.get('importacao_tipo') == 'delnext':
                    if not str(item.get('order_number', '')).startswith('D') or item.get('order_number', '') == "": # Se não começa com 'D' ou está vazio
                        needs_reindex = True
                elif item.get('importacao_tipo') == 'paack':
                    if not str(item.get('order_number', '')).startswith('P') or item.get('order_number', '') == "": # Se não começa com 'P' ou está vazio
                        needs_reindex = True

                if needs_reindex:
                    if item.get('importacao_tipo') == 'manual':
                        manual_counter += 1
                        item['order_number'] = str(manual_counter)
                    elif item.get('importacao_tipo') == 'delnext':
                        delnext_counter += 1
                        item['order_number'] = f"D{delnext_counter}"
                    elif item.get('importacao_tipo') == 'paack':
                        paack_counter += 1
                        item['order_number'] = f"P{paack_counter}"

            origens = list({item.get('importacao_tipo', 'manual') for item in lista_atual})
            session['lista'] = lista_atual
            session.modified = True
            logger.info(f"Importação concluída. Total de itens na sessão: {len(lista_atual)}. Origens: {origens}")

            return jsonify({
                "success": True,
                "lista": lista_atual,
                "origens": origens,
                "total": len(lista_atual)
            })

        except Exception as e:
            logger.error(f"Erro ao processar arquivo durante a importação: {str(e)}", exc_info=True)
            return jsonify({"success": False, "msg": f"Erro ao processar arquivo: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Erro geral na importação (antes do processamento do arquivo): {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro na importação: {str(e)}"}), 500

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
        logger.error(f"Erro ao recuperar sessão: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": str(e)}), 500

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    try:
        data = request.get_json()
        idx = int(data.get('idx', -1))
        # Obter o endereço e cep enviados pelo navegador
        endereco = data.get('endereco', '')
        cep = data.get('cep', '')

        lista_atual = session.get('lista', [])
        if idx < 0 or idx >= len(lista_atual):
            return jsonify({"success": False, "msg": "Índice inválido"}), 400

        # Atualizar o item na lista da sessão com os novos dados ANTES de validar
        lista_atual[idx]['address'] = endereco
        lista_atual[idx]['cep'] = cep

        # Validar o novo endereço com o Google
        res_google = valida_rua_google_cache(endereco, cep)

        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = res_google.get('route_encontrada', '')
        rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or
                   normalizar(rua_google) in normalizar(rua_digitada))
        cep_ok = cep == res_google.get('postal_code_encontrado', '')

        # Atualizar o resto das informações do item
        lista_atual[idx].update({
            "status_google": res_google.get('status'),
            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
            "endereco_formatado": res_google.get('endereco_formatado', ''),
            "latitude": res_google.get('coordenadas', {}).get('lat', ''),
            "longitude": res_google.get('coordenadas', {}).get('lng', ''),
            "rua_google": rua_google,
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "freguesia": res_google.get('sublocality', '')
        })

        session['lista'] = lista_atual
        session.modified = True

        return jsonify({
            "success": True,
            "item": lista_atual[idx],
            "idx": idx
        })

    except Exception as e:
        logger.error(f"Erro na validação de linha: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500

@main_routes.route('/generate', methods=['POST'])
def generate():
    try:
        global csv_content
        lista_para_csv = session.get('lista', [])

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "order number", "name", "address", "latitude", "longitude",
            "duration", "start time", "end time", "phone", "contact",
            "notes", "color", "Group", "rua_google", "freguesia_google", "status"
        ])

        for row in lista_para_csv:
            status = "Validado"
            if not row["cep_ok"]:
                status = "CEP divergente"
            elif not row["rua_bate"]:
                status = "Rua divergente"

            writer.writerow([
                row["order_number"], "", row["address"],
                row["latitude"], row["longitude"],
                "", "", "", "", "",
                row["postal_code_encontrado"] or row["cep"],
                row["cor"], "",
                row["rua_google"],
                row.get("freguesia", ""),
                status
            ])

        csv_content = output.getvalue()
        return redirect(url_for('main.download'))

    except Exception as e:
        logger.error(f"Erro ao gerar CSV: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro ao gerar CSV: {str(e)}"}), 500

@main_routes.route('/download')
def download():
    if not csv_content:
        return redirect(url_for('main.home'))

    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )

def get_next_order_number(lista, tipo):
    """Calcula o próximo número de pedido para um determinado tipo."""
    counter = 0
    prefix = ""
    if tipo == 'manual':
        for item in lista:
            if item.get('importacao_tipo') == 'manual' and str(item.get('order_number', '')).isdigit():
                counter = max(counter, int(item.get('order_number')))
        return str(counter + 1)
    elif tipo == 'delnext':
        prefix = 'D'
        for item in lista:
            if item.get('importacao_tipo') == 'delnext' and item.get('order_number', '').startswith(prefix):
                try: counter = max(counter, int(item['order_number'][1:]))
                except ValueError: pass
        return f"{prefix}{counter + 1}"
    elif tipo == 'paack':
        prefix = 'P'
        for item in lista:
            if item.get('importacao_tipo') == 'paack' and item.get('order_number', '').startswith(prefix):
                try: counter = max(counter, int(item['order_number'][1:]))
                except ValueError: pass
        return f"{prefix}{counter + 1}"
    return str(len(lista) + 1)


@main_routes.route('/api/add-address', methods=['POST'])
def add_address():
    try:
        lista_atual = session.get('lista', [])

        novo_item = {
            "order_number": get_next_order_number(lista_atual, 'manual'),
            "address": "", "cep": "", "status_google": "NÃO VALIDADO",
            "postal_code_encontrado": "", "endereco_formatado": "",
            "latitude": "", "longitude": "", "rua_google": "",
            "cep_ok": False, "rua_bate": False, "freguesia": "",
            "importacao_tipo": "manual", "cor": cor_por_tipo("manual")
        }

        lista_atual.append(novo_item)
        session['lista'] = lista_atual
        session.modified = True

        return jsonify({
            "success": True,
            "item": novo_item,
            "idx": len(lista_atual) - 1 # Retorna o índice do novo item
        })
    except Exception as e:
        logger.error(f"Erro ao adicionar endereço: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": str(e)}), 500

@main_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        idx = data.get('idx')
        lat = data.get('lat')
        lng = data.get('lng')

        if None in [idx, lat, lng]:
            return jsonify({'success': False, 'msg': 'Dados incompletos'}), 400

        api_key = os.environ.get('GOOGLE_API_KEY', '')
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{lat},{lng}",
            'key': api_key,
            'region': 'pt',
            'language': 'pt-PT'
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if not data.get('results'):
            return jsonify({'success': False, 'msg': 'Endereço não encontrado'})

        result = data['results'][0]
        address = result['formatted_address']
        postal_code = next(
            (c['long_name'] for c in result['address_components']
             if 'postal_code' in c['types']),
            ''
        )

        # Atualizar sessão
        lista_atual = session.get('lista', [])
        if 0 <= idx < len(lista_atual):
            lista_atual[idx].update({
                "latitude": lat,
                "longitude": lng,
                "address": address,
                "cep": postal_code,
                "status_google": "OK",
                "postal_code_encontrado": postal_code,
                "endereco_formatado": address,
                "cep_ok": True,
                "rua_bate": True
            })
            session['lista'] = lista_atual
            session.modified = True

        return jsonify({
            'success': True,
            'address': address,
            'cep': postal_code,
            'item': lista_atual[idx] if 0 <= idx < len(lista_atual) else None
        })

    except requests.Timeout:
        return jsonify({'success': False, 'msg': 'Timeout ao conectar com o Google Maps'}), 504
    except Exception as e:
        logger.error(f"Erro no reverse-geocode: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'msg': str(e)}), 500
