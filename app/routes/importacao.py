# app/routes/importacao.py

from flask import Blueprint, request, session, redirect, url_for
import pandas as pd
from app.utils.google import valida_rua_google_cache
from app.utils.helpers import normalizar, registro_unico, cor_por_tipo
import logging

logger = logging.getLogger(__name__)
importacao_bp = Blueprint('importacao', __name__)
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'txt'}

def extensao_permitida(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@importacao_bp.route('/import_planilha', methods=['POST'])
def import_planilha():
    """
    Processa o upload do arquivo, salva os dados na sessão e redireciona
    para a página de visualização.
    """
    try:
        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()

        if not file or not empresa or not extensao_permitida(file.filename):
            # Idealmente, aqui se usaria flash messages para notificar o erro
            return redirect(url_for('preview.home'))

        # Limpa a sessão para garantir que é uma importação nova
        session['lista'] = []

        df = None
        try:
            header_row = 1 if empresa == 'delnext' else 0
            if file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file, header=header_row)
            else:
                df = pd.read_csv(file, header=header_row, sep=None, engine='python', on_bad_lines='skip')
        except Exception as e:
            logger.error(f"Erro ao ler arquivo para {empresa}: {e}")
            return redirect(url_for('preview.home'))

        if df.empty:
            return redirect(url_for('preview.home'))

        # Mapeamento flexível de colunas
        df.columns = [str(c).lower().strip() for c in df.columns]
        nomes_col_end = ['endereco', 'morada', 'address']
        nomes_col_cep = ['cep', 'código postal', 'codigo postal', 'postal_code']
        
        col_end = next((c for c in df.columns if c in nomes_col_end), None)
        col_cep = next((c for c in df.columns if c in nomes_col_cep), None)

        if not col_end or not col_cep:
            return redirect(url_for('preview.home'))

        # Processamento das linhas
        lista_importada = []
        for _, row in df.iterrows():
            endereco = str(row[col_end]).strip()
            cep = str(row[col_cep]).strip()
            if not endereco or not cep: continue

            res_google = valida_rua_google_cache(endereco, cep)
            novo = {
                "order_number": "", "address": endereco, "cep": cep,
                "status_google": res_google.get('status', 'NÃO VALIDADO'),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "importacao_tipo": empresa, "cor": cor_por_tipo(empresa),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "endereco_formatado": res_google.get('endereco_formatado', ''),
                "rua_google": res_google.get('route_encontrada', ''),
                "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', '')),
                "freguesia": res_google.get('sublocality', '')
            }
            if registro_unico(lista_importada, novo):
                lista_importada.append(novo)
        
        # Reindexação de 'order_number'
        for i, item in enumerate(lista_importada, 1):
            prefix = 'D' if item['importacao_tipo'] == 'delnext' else 'P'
            item['order_number'] = f"{prefix}{i}"

        session['lista'] = lista_importada
        session.modified = True
        
        # --- MUDANÇA PRINCIPAL: REDIRECIONA PARA A PÁGINA DO MAPA ---
        return redirect(url_for('preview.preview_page'))

    except Exception as e:
        logger.error(f"Erro crítico na importação: {str(e)}", exc_info=True)
        return redirect(url_for('preview.home'))
