# app/routes/importacao.py

from flask import Blueprint, request, session, redirect, url_for, flash
from app.utils.google import valida_rua_google
from app.utils.helpers import normalizar, registro_unico, cor_por_tipo
from app.utils import parser
import pandas as pd
import logging
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)
importacao_bp = Blueprint('importacao', __name__)
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'txt'}

def extensao_permitida(filename: str) -> bool:
    """Verifica se a extensão do ficheiro é permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _processa_e_geocodifica(empresa: str, enderecos: list, ceps: list, order_numbers: list) -> list:
    """
    Função auxiliar que recebe os dados extraídos, geocodifica-os
    e retorna uma lista de dicionários pronta para a sessão.
    """
    lista_processada = []
    if not enderecos:
        return lista_processada
        
    logger.info(f"Geocodificando {len(enderecos)} endereços para o formato '{empresa}'...")
    for i, (endereco, cep) in enumerate(zip(enderecos, ceps)):
        order_number = order_numbers[i] if i < len(order_numbers) and order_numbers[i] else f"{(empresa or 'item').upper()}-{i+1}"
        
        res_google = valida_rua_google(endereco, cep)
        novo_item = {
            "order_number": order_number, "address": endereco, "cep": cep,
            "status_google": res_google.get('status', 'ERRO'),
            "latitude": res_google.get('coordenadas', {}).get('lat', ''),
            "longitude": res_google.get('coordenadas', {}).get('lng', ''),
            "importacao_tipo": empresa, "cor": cor_por_tipo(empresa),
            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
            "endereco_formatado": res_google.get('endereco_formatado', ''),
            "rua_google": res_google.get('route_encontrada', ''),
            "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
            "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', '')),
            "freguesia": res_google.get('sublocality', ''),
            "locality": res_google.get('locality', '')
        }
        # A função 'registro_unico' do helpers pode ser usada aqui para evitar duplos na mesma importação
        if registro_unico(lista_processada, novo_item):
            lista_processada.append(novo_item)
            
    return lista_processada

def _processar_ficheiro(file: FileStorage) -> list:
    """Processa um único ficheiro, deteta o seu formato e retorna uma lista de itens processados."""
    if not file or not extensao_permitida(file.filename):
        return []

    logger.info(f"Processando ficheiro: {file.filename}")
    
    # Caso 1: Ficheiro de texto (assumido como Paack)
    if file.filename.lower().endswith('.txt'):
        conteudo = file.read().decode("utf-8")
        enderecos, ceps, order_numbers = parser.parse_paack_texto(conteudo)
        return _processa_e_geocodifica('paack', enderecos, ceps, order_numbers)
    
    # Caso 2: Ficheiro estruturado (Excel/CSV)
    try:
        df = pd.read_excel(file)
    except Exception:
        file.seek(0)
        df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8')
    
    if df.empty:
        logger.warning(f"DataFrame vazio para o ficheiro {file.filename}")
        return []

    formato = parser.detectar_formato_df(df)
    if not formato:
        logger.warning(f"Formato não reconhecido para {file.filename}. A ignorar.")
        return []

    enderecos, ceps, order_numbers = parser.parse_dataframe(df, formato)
    return _processa_e_geocodifica(formato, enderecos, ceps, order_numbers)

def _processar_texto_manual(texto: str) -> list:
    """Processa o texto da área de texto manual (assumido como Paack) e retorna itens processados."""
    if not texto:
        return []
    logger.info("Processando endereços da área de texto manual.")
    enderecos, ceps, order_numbers = parser.parse_paack_texto(texto)
    # A entrada manual é tratada como 'paack' para ter prioridade na deduplicação
    return _processa_e_geocodifica('paack', enderecos, ceps, order_numbers)

def _unificar_e_deduplicar(lista_de_itens: list) -> list:
    """Unifica resultados, deduplica com prioridade para o formato 'paack'."""
    registros_unicos = {}
    logger.info(f"Deduplicando {len(lista_de_itens)} itens no total...")
    
    for item in lista_de_itens:
        # Chave de unicidade baseada no endereço e CEP normalizados
        chave = (normalizar(item['address']), normalizar(item['cep']))
        
        # Se a chave já existe, só substitui se o novo item for 'paack'
        if chave in registros_unicos:
            if 'paack' in item['importacao_tipo']:
                registros_unicos[chave] = item
        else:
            registros_unicos[chave] = item
            
    lista_deduplicada = list(registros_unicos.values())
    logger.info(f"Resultaram {len(lista_deduplicada)} itens únicos após deduplicação.")
    return lista_deduplicada

def _reindexar_lista(lista: list) -> list:
    """Re-indexa o order_number de toda a lista final de 1 a N."""
    for idx, item in enumerate(lista, 1):
        item['order_number'] = str(idx)
    return lista

@importacao_bp.route('/import_planilha', methods=['POST'])
def import_planilha():
    """
    Ponto de entrada unificado para importação. Aceita múltiplos ficheiros e texto manual,
    processa, deduplica, e redireciona para a página de pré-visualização.
    """
    try:
        files = request.files.getlist('planilhas')
        texto_manual = request.form.get('enderecos_manuais', '').strip()

        if not files and not texto_manual:
            flash("Adicione pelo menos um ficheiro ou endereço manual.", "warning")
            return redirect(url_for('preview.home'))

        todos_os_itens = []

        # 1. Processar todos os ficheiros enviados
        for file in files:
            todos_os_itens.extend(_processar_ficheiro(file))

        # 2. Processar o texto da área manual
        todos_os_itens.extend(_processar_texto_manual(texto_manual))

        if not todos_os_itens:
            flash("Nenhum endereço válido foi encontrado nas fontes fornecidas.", "warning")
            return redirect(url_for('preview.home'))

        # 3. Deduplicar com prioridade e Re-indexar
        lista_unica = _unificar_e_deduplicar(todos_os_itens)
        lista_final = _reindexar_lista(lista_unica)

        # 4. Salvar na sessão e redirecionar
        session.clear()
        session['lista'] = lista_final
        session.modified = True

        flash(f"{len(lista_final)} endereços únicos foram importados com sucesso!", "success")
        return redirect(url_for('preview.preview'))

    except Exception as e:
        logger.error(f"[importacao] Erro crítico durante a importação unificada: {str(e)}", exc_info=True)
        flash(f"Ocorreu um erro inesperado durante a importação: {str(e)}", "danger")
        return redirect(url_for('preview.home'))
