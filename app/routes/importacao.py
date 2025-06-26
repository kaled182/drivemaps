# app/routes/importacao.py

from flask import Blueprint, request, session, redirect, url_for, flash
from app.utils.geocoder import valida_rua  # <<<< AGORA USA O DISPATCHER DINÂMICO!
from app.utils.helpers import normalizar, registro_unico, cor_por_tipo
from app.utils import parser
import pandas as pd
import logging
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)
importacao_bp = Blueprint('importacao', __name__)
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'txt'}

def extensao_permitida(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _processa_e_geocodifica(empresa: str, enderecos: list, ceps: list, order_numbers: list) -> list:
    lista_processada = []
    if not enderecos:
        return lista_processada

    logger.info(f"Geocodificando {len(enderecos)} endereços para o formato '{empresa}'...")
    for i, (endereco, cep) in enumerate(zip(enderecos, ceps)):
        order_number = order_numbers[i] if i < len(order_numbers) and order_numbers[i] else f"{(empresa or 'item').upper()}-{i+1}"

        res_geo = valida_rua(endereco, cep)  # USANDO O DISPATCHER
        novo_item = {
            "order_number": order_number, "address": endereco, "cep": cep,
            "status_google": res_geo.get('status', 'ERRO'),
            "latitude": res_geo.get('coordenadas', {}).get('lat', ''),
            "longitude": res_geo.get('coordenadas', {}).get('lng', ''),
            "importacao_tipo": empresa, "cor": cor_por_tipo(empresa),
            "postal_code_encontrado": res_geo.get('postal_code_encontrado', ''),
            "endereco_formatado": res_geo.get('endereco_formatado', ''),
            "rua_google": res_geo.get('route_encontrada', ''),
            "cep_ok": cep == res_geo.get('postal_code_encontrado', ''),
            "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_geo.get('route_encontrada', '')),
            "freguesia": res_geo.get('sublocality', ''),
            "locality": res_geo.get('locality', '')
        }
        if registro_unico(lista_processada, novo_item):
            lista_processada.append(novo_item)
    return lista_processada

def _processar_ficheiro(file: FileStorage) -> list:
    if not file or not extensao_permitida(file.filename):
        return []

    logger.info(f"Processando ficheiro: {file.filename}")

    if file.filename.lower().endswith('.txt'):
        conteudo = file.read().decode("utf-8")
        enderecos, ceps, order_numbers = parser.parse_paack_texto(conteudo)
        return _processa_e_geocodifica('paack', enderecos, ceps, order_numbers)

    # -- Tenta ignorar a primeira linha, depois tenta normal se der erro ou detectar menos de 2 colunas --
    try:
        file.seek(0)
        df = pd.read_excel(file, skiprows=1)
        if df.empty or len(df.columns) < 2:
            file.seek(0)
            df = pd.read_excel(file)
    except Exception:
        file.seek(0)
        try:
            df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8', skiprows=1)
            if df.empty or len(df.columns) < 2:
                file.seek(0)
                df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8')
        except Exception as err:
            logger.error(f"Erro ao ler arquivo como excel/csv: {err}")
            return []

    logger.debug(f"[IMPORTACAO] Colunas detectadas: {list(df.columns)}")
    logger.debug(f"[IMPORTACAO] Primeiras linhas: {df.head().to_dict()}")

    if df.empty:
        logger.warning(f"DataFrame vazio para o ficheiro {file.filename}")
        return []

    formato = parser.detectar_formato_df(df)
    logger.info(f"Formato detectado: {formato}")

    if not formato:
        logger.warning(f"Formato não reconhecido para {file.filename}. A ignorar.")
        return []

    enderecos, ceps, order_numbers = parser.parse_dataframe(df, formato)
    return _processa_e_geocodifica(formato, enderecos, ceps, order_numbers)

def _processar_texto_manual(texto: str) -> list:
    if not texto:
        return []
    logger.info("Processando endereços da área de texto manual.")
    enderecos, ceps, order_numbers = parser.parse_paack_texto(texto)
    return _processa_e_geocodifica('paack', enderecos, ceps, order_numbers)

def _unificar_e_deduplicar(lista_de_itens: list) -> list:
    registros_unicos = {}
    logger.info(f"Deduplicando {len(lista_de_itens)} itens no total...")

    for item in lista_de_itens:
        chave = (normalizar(item['address']), normalizar(item['cep']))
        if chave in registros_unicos:
            if 'paack' in item['importacao_tipo']:
                registros_unicos[chave] = item
        else:
            registros_unicos[chave] = item
    lista_deduplicada = list(registros_unicos.values())
    logger.info(f"Resultaram {len(lista_deduplicada)} itens únicos após deduplicação.")
    return lista_deduplicada

def _reindexar_lista(lista: list) -> list:
    """Mantém o order_number original para Paack e garante D1, D2... para Delnext"""
    d_count = 1
    for item in lista:
        if str(item.get("importacao_tipo", "")).lower() == "delnext":
            item['order_number'] = f"D{d_count}"
            d_count += 1
        # Paack mantém order_number como está
    return lista

@importacao_bp.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        files = request.files.getlist('planilhas')
        texto_manual = request.form.get('enderecos_manuais', '').strip()

        if not files and not texto_manual:
            flash("Adicione pelo menos um ficheiro ou endereço manual.", "warning")
            return redirect(url_for('preview.home'))

        todos_os_itens = []

        for file in files:
            todos_os_itens.extend(_processar_ficheiro(file))
        todos_os_itens.extend(_processar_texto_manual(texto_manual))

        if not todos_os_itens:
            flash("Nenhum endereço válido foi encontrado nas fontes fornecidas.", "warning")
            return redirect(url_for('preview.home'))

        lista_unica = _unificar_e_deduplicar(todos_os_itens)
        lista_final = _reindexar_lista(lista_unica)

        session.clear()
        session['lista'] = lista_final
        session.modified = True

        flash(f"{len(lista_final)} endereços únicos foram importados com sucesso!", "success")
        return redirect(url_for('preview.preview'))

    except Exception as e:
        logger.error(f"[importacao] Erro crítico durante a importação unificada: {str(e)}", exc_info=True)
        flash(f"Ocorreu um erro inesperado durante a importação: {str(e)}", "danger")
        return redirect(url_for('preview.home'))
