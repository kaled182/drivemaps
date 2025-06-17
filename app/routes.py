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
    """Verifica se um registro (endereço + cep + tipo) já existe na lista para evitar duplicatas)."""
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
                    # O 'order_number' aqui será preenchido pelo re-indexador ao final
                    # ou pode ser pego do input, se houver um para o preview.
                    # Por padrão, o preview manual não tem um order_number específico.
                    numero_pacote_str = linhas[i+3] if (i+3) < len(linhas) else ""
                    # Se o numero_pacote_str for um número válido, use-o como sugestão.
                    # O re-indexador final irá formatar corretamente.
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
                    
                    if registro_unico(session.get('lista', []) + lista_preview_novos, novo):
                        lista_preview_novos.append(novo)
                    else:
                        logger.info(f"Registro duplicado no Preview ignorado: {linha}, {cep}")
                    i += 4
                else:
                    i += 1
            else:
                i += 1
        
        lista_atual = session.get('lista', [])
        lista_atual.extend(lista_preview_novos) # Adiciona os novos itens do preview

        # --- Lógica de re-atribuição de order_number para toda a lista (Consistente com import_planilha) ---
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

        # Atribui novos order_numbers ou corrige formatos inválidos
        for item in lista_atual:
            needs_reindex = False
            if item.get('importacao_tipo') == 'manual':
                if not str(item.get('order_number', '')).isdigit() or item.get('order_number', '') == "":
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'delnext':
                if not str(item.get('order_number', '')).startswith('D') or item.get('order_number', '') == "":
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'paack':
                if not str(item.get('order_number', '')).startswith('P') or item.get('order_number', '') == "":
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
                        # LEITURA MAIS SEGURA PARA CSV/TXT
                        content = file.read().decode('utf-8', errors='ignore') # Adicionado errors='ignore'
                        # Pega a primeira linha não vazia para sniffer
                        first_line_for_sniffer = ""
                        lines = content.splitlines()
                        if len(lines) > 1: # Pula o cabeçalho (header=1)
                            for line in lines[1:]: # Começa da segunda linha para detectar o separador
                                if line.strip():
                                    first_line_for_sniffer = line
                                    break
                        if not first_line_for_sniffer:
                            # Se não encontrou linha para sniffer após o header, tenta com a primeira linha
                            if lines and lines[0].strip():
                                first_line_for_sniffer = lines[0].strip()
                            else:
                                raise ValueError("Conteúdo CSV/TXT vazio ou sem linhas válidas para detecção de separador.")

                        dialect = csv.Sniffer().sniff(first_line_for_sniffer, delimiters=[',', ';'])
                        file.seek(0)
                        # Usar io.BytesIO para compatibilidade com pd.read_csv quando o 'file' já foi lido
                        df = pd.read_csv(io.BytesIO(content.encode('utf-8')), header=1, sep=dialect.delimiter)
                    except Exception as csv_err:
                        logger.warning(f"Erro ao tentar detectar separador CSV para Delnext, tentando padrão: {csv_err}")
                        file.seek(0)
                        try:
                            df = pd.read_csv(file, header=1, sep=',')
                        except Exception as e_comma:
                            logger.warning(f"Leitura CSV Delnext com vírgula falhou, tentando ponto e vírgula: {e_comma}")
                            file.seek(0)
                            df = pd.read_csv(file, header=1, sep=';')
                else:
                    return jsonify({
                        "success": False,
                        "msg": "Formato de arquivo Delnext não suportado. Use .xlsx, .xls, .csv ou .txt"
                    }), 400
                
                if df.empty:
                    logger.error("DataFrame Delnext vazio após a leitura. Verifique o formato ou o header.")
                    return jsonify({
                        "success": False,
                        "msg": "A planilha Delnext está vazia ou o formato é inválido após ignorar a primeira linha."
                    }), 400

                df.columns = df.columns.astype(str) # Garante que nomes de colunas são strings
                
                col_morada = next((c for c in df.columns if 'morada' in c.lower()), None)
                col_cep = next((c for c in df.columns if 'código postal' in c.lower() or 'codigo postal' in c.lower()), None)
                
                if not col_morada or not col_cep:
                    logger.error(f"Colunas 'Morada' ou 'Código Postal' não encontradas no arquivo Delnext. Colunas disponíveis: {df.columns.tolist()}")
                    return jsonify({
                        "success": False,
                        "msg": "Estrutura inválida. A planilha Delnext deve conter colunas de 'Morada' e 'Código Postal' (ignorando maiúsculas/minúsculas)."
                    }), 400
                
                for index, row in df.iterrows():
                    endereco = str(row[col_morada]).strip()
                    cep = str(row[col_cep]).strip()
                    
                    if not endereco or not cep:
                        logger.warning(f"Linha {index+2} (após cabeçalho) ignorada por conter endereço ou CEP vazio: Endereço='{endereco}', CEP='{cep}'")
                        continue 
                        
                    # Lógica de formatação de CEP (mantida do código anterior)
                    cep = re.sub(r'[^\d-]', '', cep)
                    if len(cep) == 8 and '-' not in cep: # Ex: "12345678" vira "1234-5678" -> "1234-567"
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 7 and '-' not in cep: # Ex: "1234567" -> "1234-567"
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 9 and cep.count('-') == 1 and len(cep.replace('-', '')) == 8: # Ex: "1234-5678" Delnext pode vir com 8 digitos
                        cep = cep[:8] # Corta para 1234-567 (mantendo o formato padrão pt)
                    elif len(cep) > 8 and '-' in cep and len(cep.replace('-', '')) > 7: # Outros formatos, tenta normalizar
                         # Tenta pegar apenas 4 primeiros digitos, hífen e 3 proximos
                        numbers = re.sub(r'\D', '', cep) # Remove tudo que não for dígito
                        if len(numbers) >= 7:
                            cep = f"{numbers[:4]}-{numbers[4:7]}"
                        else: # Se não tiver 7 dígitos, usa como está e a validação do google vai falhar
                            pass

                    logger.info(f"Processando linha Delnext {index+2}: Endereço='{endereco}', CEP formatado='{cep}'")
                    
                    res_google = valida_rua_google_cache(endereco, cep)
                    rua_digitada = endereco.split(',')[0] if endereco else ''
                    rua_google = res_google.get('route_encontrada', '')
                    
                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                                  normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = (cep == res_google.get('postal_code_encontrado', ''))
                    
                    novo = {
                        "order_number": "", 
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
                    
                    if registro_unico(lista_atual, novo): # Verifica duplicidade com a lista atual
                        novos_itens_importados.append(novo) 
                    else:
                        logger.info(f"Registro duplicado Delnext ignorado: {endereco}, {cep}")

            elif empresa == "paack":
                file.seek(0)
                filename = file.filename.lower()
                
                if filename.endswith(('.xlsx', '.xls')):
                    logger.info("Processando arquivo Paack como Excel.")
                    df = pd.read_excel(file, header=0) 
                elif filename.endswith(('.csv', '.txt')):
                    logger.info("Processando arquivo Paack como CSV/TXT.")
                    try:
                        # LEITURA MAIS SEGURA PARA CSV/TXT
                        content = file.read().decode('utf-8', errors='ignore') # Adicionado errors='ignore'
                        first_line_for_sniffer = ""
                        lines = content.splitlines()
                        if lines: # Pega a primeira linha para sniffer (header=0)
                            first_line_for_sniffer = lines[0].strip()
                        if not first_line_for_sniffer:
                            raise ValueError("Conteúdo CSV/TXT vazio ou sem linhas válidas para detecção de separador.")

                        dialect = csv.Sniffer().sniff(first_line_for_sniffer, delimiters=[',', ';'])
                        file.seek(0)
                        df = pd.read_csv(io.BytesIO(content.encode('utf-8')), header=0, sep=dialect.delimiter)
                    except Exception as csv_err:
                        logger.warning(f"Erro ao tentar detectar separador CSV para Paack, tentando padrão: {csv_err}")
                        file.seek(0)
                        try:
                            df = pd.read_csv(file, header=0, sep=',')
                        except Exception as e_comma:
                            logger.warning(f"Leitura CSV Paack com vírgula falhou, tentando ponto e vírgula: {e_comma}")
                            file.seek(0)
                            df = pd.read_csv(file, header=0, sep=';')
                else:
                     return jsonify({
                        "success": False,
                        "msg": "Formato de arquivo Paack não suportado. Use .xlsx, .xls, .csv ou .txt"
                    }), 400

                if df.empty:
                    logger.error("DataFrame Paack vazio após a leitura. Verifique o formato ou o header.")
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

                for index, row in df.iterrows():
                    endereco = str(row[col_end]).strip()
                    cep = str(row[col_cep]).strip()

                    if not endereco or not cep:
                        logger.warning(f"Linha {index+1} (Paack) ignorada por conter endereço ou CEP vazio: Endereço='{endereco}', CEP='{cep}'")
                        continue

                    # Lógica de formatação de CEP (mantida do código anterior)
                    cep = re.sub(r'[^\d-]', '', cep)
                    if len(cep) == 8 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 7 and '-' not in cep:
                        cep = f"{cep[:4]}-{cep[4:]}"
                    elif len(cep) == 9 and cep.count('-') == 1 and len(cep.replace('-', '')) == 8:
                        cep = cep[:8]
                    elif len(cep) > 8 and '-' in cep and len(cep.replace('-', '')) > 7:
                        numbers = re.sub(r'\D', '', cep)
                        if len(numbers) >= 7:
                            cep = f"{numbers[:4]}-{numbers[4:7]}"
                        else:
                            pass

                    logger.info(f"Processando linha Paack {index+1}: Endereço='{endereco}', CEP formatado='{cep}'")

                    res_google = valida_rua_google_cache(endereco, cep)
                    rua_digitada = endereco.split(',')[0] if endereco else ''
                    rua_google = res_google.get('route_encontrada', '')
                    
                    rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                                  normalizar(rua_google) in normalizar(rua_digitada))
                    cep_ok = (cep == res_google.get('postal_code_encontrado', ''))

                    novo = {
                        "order_number": "", 
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
                    
                    if registro_unico(lista_atual, novo): # Verifica duplicidade com a lista atual
                        novos_itens_importados.append(novo)
                    else:
                        logger.info(f"Registro duplicado Paack ignorado: {endereco}, {cep}")

            else:
                return jsonify({"success": False, "msg": "Empresa não suportada"}), 400

            # --- Adiciona todos os novos itens válidos à lista atual (se não forem duplicatas) ---
            # Extendemos a lista_atual com os novos itens validados
            # Isso assegura que os itens antigos não são apagados, apenas os novos são adicionados
            lista_atual.extend(novos_itens_importados)

            # --- Lógica de re-atribuição de order_number para toda a lista ---
            # Garante que os order_numbers são únicos e sequenciais por tipo (D, P, ou numérico para manual)
            manual_counter = 0
            delnext_counter = 0
            paack_counter = 0

            # Primeiro, encontra o maior número atual para cada tipo de importação
            # Isso é importante para continuar a sequência se já existirem itens
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
                    pass # Ignora order_numbers mal formatados ou vazios

            # Depois, itera sobre a lista_atual e atribui/corrige os order_numbers
            for item in lista_atual:
                needs_reindex = False
                if item.get('importacao_tipo') == 'manual':
                    if not str(item.get('order_number', '')).isdigit() or item.get('order_number', '') == "":
                        needs_reindex = True
                elif item.get('importacao_tipo') == 'delnext':
                    if not str(item.get('order_number', '')).startswith('D') or item.get('order_number', '') == "":
                        needs_reindex = True
                elif item.get('importacao_tipo') == 'paack':
                    if not str(item.get('order_number', '')).startswith('P') or item.get('order_number', '') == "":
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
                # Se o order_number já está no formato correto para o tipo, ele é mantido.

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
    """Retorna os dados da sessão. Útil para depuração ou inicialização do frontend."""
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
    """Valida um único endereço recebido do frontend."""
    try:
        data = request.get_json()
        idx = int(data.get('idx', -1))
        
        # Use os dados de endereço e CEP enviados do frontend, pois o usuário pode ter editado.
        endereco_from_form = data.get('endereco', '')
        cep_from_form = data.get('cep', '')

        lista_atual = session.get('lista', [])
        if idx < 0 or idx >= len(lista_atual):
            logger.error(f"Índice inválido para validação de linha: {idx}")
            return jsonify({"success": False, "msg": "Índice inválido"}), 400

        item = lista_atual[idx] # Pega o item existente da sessão

        # ATUALIZA o item da sessão com os dados potencialmente editados do frontend antes de validar
        item["address"] = endereco_from_form
        item["cep"] = cep_from_form

        # Formatar CEP (garantir que esteja no formato PT antes de enviar para o Google)
        item["cep"] = re.sub(r'[^\d-]', '', item["cep"])
        if len(item["cep"]) == 8 and '-' not in item["cep"]:
            item["cep"] = f"{item['cep'][:4]}-{item['cep'][4:]}"
        elif len(item["cep"]) == 7 and '-' not in item["cep"]:
            item["cep"] = f"{item['cep'][:4]}-{item['cep'][4:]}"
        elif len(item["cep"]) == 9 and item["cep"].count('-') == 1 and len(item["cep"].replace('-', '')) == 8:
            item["cep"] = item["cep"][:8]
        elif len(item["cep"]) > 8 and '-' in item["cep"] and len(item["cep"].replace('-', '')) > 7:
            numbers = re.sub(r'\D', '', item["cep"])
            if len(numbers) >= 7:
                item["cep"] = f"{numbers[:4]}-{numbers[4:7]}"
            else:
                pass


        res_google = valida_rua_google_cache(item["address"], item["cep"]) 
        
        rua_digitada = item["address"].split(',')[0] if item["address"] else ''
        rua_google = res_google.get('route_encontrada', '')
        
        # A comparação de ruas foi ajustada para ser mais flexível, verificar se uma contém a outra
        rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                   normalizar(rua_google) in normalizar(rua_digitada))
        cep_ok = item["cep"] == res_google.get('postal_code_encontrado', '')
        
        item.update({
            "status_google": res_google.get('status'),
            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
            "latitude": res_google.get('coordenadas', {}).get('lat', ''),
            "longitude": res_google.get('coordenadas', {}).get('lng', ''),
            "rua_google": rua_google,
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "freguesia": res_google.get('sublocality', ''),
            "endereco_formatado": res_google.get('endereco_formatado', item["address"]) # Atualiza o endereço formatado
        })
        
        session['lista'] = lista_atual # Salva a lista atualizada na sessão
        session.modified = True
        
        return jsonify({
            "success": True,
            "item": item, # Retorna o item COMPLETAMENTE atualizado
            "idx": idx
        })
        
    except Exception as e:
        logger.error(f"Erro na validação de linha: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500

@main_routes.route('/api/validar-tudo', methods=['POST'])
def validar_tudo():
    """Valida todos os endereços na sessão ou na lista fornecida."""
    try:
        data = request.get_json()
        lista_from_frontend = data.get('lista', []) 

        lista_atual = session.get('lista', []) 
        
        if not lista_atual and not lista_from_frontend:
            return jsonify({"success": True, "msg": "Nenhum endereço para validar."})

        # Sincroniza a lista da sessão com os valores mais recentes do frontend
        # Isso é crucial se o usuário editou vários campos antes de clicar em "Validar Tudo"
        # Usamos os índices para garantir que estamos atualizando o item correto na lista da sessão
        for i, item_from_fe in enumerate(lista_from_frontend):
            if i < len(lista_atual):
                lista_atual[i]["address"] = item_from_fe.get("address", "")
                lista_atual[i]["cep"] = item_from_fe.get("cep", "")
                # Outros campos que podem ser editados na UI também deveriam ser sincronizados aqui se aplicável
            else:
                # Caso um item novo que foi adicionado no FE e não foi salvo no BE ainda,
                # ele não estará em lista_atual. Pode ser adicionado aqui para validação,
                # mas o fluxo ideal seria adicioná-lo via /api/add-manual-address primeiro.
                logger.warning(f"Item {i} do frontend não encontrado na sessão durante validar-tudo. Pode ser um novo item não salvo previamente.")
                # Por agora, vamos apenas trabalhar com itens já existentes na sessão
                # se você precisar validar novos itens em massa, adicione-os à sessão ANTES desta chamada.


        # Loop para validar cada item AGORA na lista_atual (que está sincronizada com o frontend)
        for idx, item in enumerate(lista_atual): # Itera sobre a lista_atual sincronizada
            # Formatar CEP antes da validação
            item["cep"] = re.sub(r'[^\d-]', '', item["cep"])
            if len(item["cep"]) == 8 and '-' not in item["cep"]:
                item["cep"] = f"{item['cep'][:4]}-{item['cep'][4:]}"
            elif len(item["cep"]) == 7 and '-' not in item["cep"]:
                item["cep"] = f"{item['cep'][:4]}-{item['cep'][4:]}"
            elif len(item["cep"]) == 9 and item["cep"].count('-') == 1 and len(item["cep"].replace('-', '')) == 8:
                item["cep"] = item["cep"][:8]
            elif len(item["cep"]) > 8 and '-' in item["cep"] and len(item["cep"].replace('-', '')) > 7:
                numbers = re.sub(r'\D', '', item["cep"])
                if len(numbers) >= 7:
                    item["cep"] = f"{numbers[:4]}-{numbers[4:7]}"
                else:
                    pass

            res_google = valida_rua_google_cache(item["address"], item["cep"])
            
            rua_digitada = item["address"].split(',')[0] if item["address"] else ''
            rua_google = res_google.get('route_encontrada', '')
            rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                       normalizar(rua_google) in normalizar(rua_digitada))
            cep_ok = item["cep"] == res_google.get('postal_code_encontrado', '')
            
            lista_atual[idx].update({ # Atualiza o item diretamente na lista_atual
                "status_google": res_google.get('status'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "rua_google": rua_google,
                "cep_ok": cep_ok,
                "rua_bate": rua_bate,
                "freguesia": res_google.get('sublocality', ''),
                "endereco_formatado": res_google.get('endereco_formatado', item["address"])
            })
            
        session['lista'] = lista_atual
        session.modified = True
        
        return jsonify({
            "success": True,
            "msg": "Todos os endereços foram validados com sucesso!",
            "lista": lista_atual # Retorna a lista completa atualizada
        })
        
    except Exception as e:
        logger.error(f"Erro na validação em massa: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro na validação em massa: {str(e)}"}), 500

@main_routes.route('/api/add-manual-address', methods=['POST'])
def add_manual_address():
    """Adiciona um novo endereço manual à lista e retorna o item com o novo order_number."""
    try:
        lista_atual = session.get('lista', [])

        novo = {
            "order_number": "", # Será preenchido na re-indexação final
            "address": "",
            "cep": "",
            "importacao_tipo": "manual",
            "cor": cor_por_tipo("manual"),
            "status_google": "NÃO VALIDADO", # Status inicial para novo endereço manual
            "postal_code_encontrado": "",
            "endereco_formatado": "",
            "latitude": "",
            "longitude": "",
            "rua_google": "",
            "cep_ok": False,
            "rua_bate": False,
            "freguesia": ""
        }
        
        lista_atual.append(novo) # Adiciona o novo item à lista

        # Re-atribui os order_numbers para toda a lista para manter a sequência
        manual_counter = 0
        delnext_counter = 0
        paack_counter = 0

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

        # Atribui novos order_numbers ou corrige formatos inválidos
        for item in lista_atual:
            needs_reindex = False
            if item.get('importacao_tipo') == 'manual':
                if not str(item.get('order_number', '')).isdigit() or item.get('order_number', '') == "":
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'delnext':
                if not str(item.get('order_number', '')).startswith('D') or item.get('order_number', '') == "":
                    needs_reindex = True
            elif item.get('importacao_tipo') == 'paack':
                if not str(item.get('order_number', '')).startswith('P') or item.get('order_number', '') == "":
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
        
        # Retorna o item recém-adicionado com o order_number já formatado
        # O último item adicionado é 'novo', e agora tem o order_number certo
        return jsonify({
            "success": True,
            "item": novo, 
            "idx": len(lista_atual) - 1 # Retorna o índice onde foi adicionado
        })

    except Exception as e:
        logger.error(f"Erro ao adicionar endereço manual: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro: {str(e)}"}), 500


@main_routes.route('/generate', methods=['POST'])
def generate():
    """Gera o arquivo CSV para download usando os dados da sessão."""
    try:
        global csv_content
        # Pegar a lista diretamente da sessão para garantir que as validações mais recentes
        # e os order_numbers formatados estejam presentes.
        lista_para_csv = session.get('lista', [])
        
        # Gerar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow([
            "order number", "name", "address", "latitude", "longitude", 
            "duration", "start time", "end time", "phone", "contact", 
            "notes", "color", "Group", "rua_google", "freguesia_google", "status"
        ])
        
        # Dados
        for row in lista_para_csv: # Iterar sobre a lista da sessão
            status = "Validado"
            if not row["cep_ok"]:
                status = "CEP divergente"
            elif not row["rua_bate"]:
                status = "Rua divergente"
                
            writer.writerow([
                row["order_number"], "", row["address"], 
                row["latitude"], row["longitude"], 
                "", "", "", "", "",
                row["postal_code_encontrado"] or row["cep"], # Notes
                row["cor"], "", # Color, Group
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
    """Fornece o arquivo CSV para download."""
    if not csv_content:
        return redirect(url_for('main.home'))
        
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )

@main_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    """Realiza a geocodificação reversa de uma coordenada (latitude, longitude) e atualiza o item na sessão."""
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
        data_google = response.json() # Renomeado para evitar conflito com 'data' da requisição Flask
        
        if not data_google.get('results'):
            logger.warning(f"Reverse geocode falhou para {lat},{lng}: Nenhum resultado encontrado.")
            return jsonify({'success': False, 'msg': 'Endereço não encontrado nas coordenadas.'})
            
        result = data_google['results'][0]
        address = result['formatted_address']
        postal_code = next(
            (c['long_name'] for c in result['address_components'] 
             if 'postal_code' in c['types']),
            ''
        )
        # Extrair rua e freguesia do resultado do Google para consistência
        route_encontrada = next((c['long_name'] for c in result['address_components'] if 'route' in c['types']), '')
        sublocality = next((c['long_name'] for c in result['address_components'] if 'sublocality' in c['types']), '')

        # Atualizar sessão
        lista_atual = session.get('lista', [])
        if 0 <= idx < len(lista_atual):
            item_to_update = lista_atual[idx]
            
            # Normaliza o CEP do Google para garantir formato PT (XXXX-XXX)
            postal_code_normalized = re.sub(r'[^\d-]', '', postal_code)
            if len(postal_code_normalized) == 8 and '-' not in postal_code_normalized:
                postal_code_normalized = f"{postal_code_normalized[:4]}-{postal_code_normalized[4:]}"
            elif len(postal_code_normalized) == 7 and '-' not in postal_code_normalized:
                 postal_code_normalized = f"{postal_code_normalized[:4]}-{postal_code_normalized[4:]}"
            elif len(postal_code_normalized) == 9 and postal_code_normalized.count('-') == 1 and len(postal_code_normalized.replace('-', '')) == 8:
                postal_code_normalized = postal_code_normalized[:8]
            elif len(postal_code_normalized) > 8 and '-' in postal_code_normalized and len(postal_code_normalized.replace('-', '')) > 7:
                numbers = re.sub(r'\D', '', postal_code_normalized)
                if len(numbers) >= 7:
                    postal_code_normalized = f"{numbers[:4]}-{numbers[4:7]}"
                else:
                    pass

            item_to_update.update({
                "latitude": lat,
                "longitude": lng,
                "address": address, # Endereço completo do Google
                "cep": postal_code_normalized, # CEP normalizado do Google
                "status_google": "OK",
                "postal_code_encontrado": postal_code_normalized, # CEP normalizado do Google
                "endereco_formatado": address,
                "cep_ok": True, # Assume que o CEP do Google é "OK"
                "rua_bate": True, # Assume que a rua bate, pois é o endereço do Google
                "rua_google": route_encontrada, # Guarda a rua encontrada pelo Google
                "freguesia": sublocality # Guarda a freguesia
            })
            session['lista'] = lista_atual
            session.modified = True

            logger.info(f"Reverse geocode sucesso para idx {idx}: {address}, {postal_code_normalized}")
            return jsonify({
                'success': True,
                'address': address,
                'cep': postal_code_normalized,
                'item': item_to_update # Retorna o item atualizado
            })
        else:
            logger.error(f"Índice {idx} fora dos limites da lista na reverse-geocode.")
            return jsonify({'success': False, 'msg': 'Erro interno ao atualizar item.'}), 500
        
    except requests.Timeout:
        logger.error(f"Timeout no reverse-geocode para {lat},{lng}.")
        return jsonify({'success': False, 'msg': 'Timeout ao conectar com o Google Maps'}), 504
    except requests.RequestException as e:
        logger.error(f"Erro de requisição Google Maps no reverse-geocode: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'msg': f'Erro na comunicação com Google Maps: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Erro geral no reverse-geocode: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'msg': str(e)}), 500
