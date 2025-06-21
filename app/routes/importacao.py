# app/routes/importacao.py
from flask import Blueprint, request, session, redirect, url_for, flash
import pandas as pd
from app.utils.google import valida_rua_google
from app.utils.helpers import normalizar, registro_unico, cor_por_tipo
from app.utils import parser
import logging
import os

logger = logging.getLogger(__name__)
importacao_bp = Blueprint('importacao', __name__)

ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'txt'}

def extensao_permitida(filename):
    """Verifica se o arquivo tem extensão permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@importacao_bp.route('/import_planilha', methods=['POST'])
def import_planilha():
    """
    Faz upload e processa uma planilha.
    Extrai, valida e geocodifica endereços, salva na sessão e redireciona para preview.
    """
    try:
        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower().strip()

        if not file or not empresa:
            flash("Selecione o ficheiro e a empresa antes de importar.", "danger")
            return redirect(url_for('preview.home'))

        if not extensao_permitida(file.filename):
            flash("Tipo de ficheiro não suportado. Use CSV, XLS, XLSX ou TXT.", "danger")
            return redirect(url_for('preview.home'))
            
        logger.info(f"[importacao] Processando ficheiro para: {empresa}")

        # --- Parsing adaptativo por empresa ---
        try:
            enderecos, ceps, order_numbers = [], [], []
            if empresa in ("delnext", "custom"):
                try:
                    df = pd.read_excel(file)
                except Exception:
                    file.seek(0)
                    df = pd.read_csv(file, encoding="utf-8", sep=None, engine='python', on_bad_lines='skip')
                enderecos, ceps, order_numbers = parser.parse_delnext(df)
            elif empresa == "paack":
                conteudo = file.read().decode("utf-8")
                enderecos, ceps, order_numbers = parser.parse_paack(conteudo)
            else:
                raise ValueError("Empresa não suportada para importação.")
        except Exception as e:
            raise ValueError(f"Não foi possível ler o ficheiro. Erro: {e}")

        if not enderecos:
            raise ValueError("Não foi possível extrair endereços do arquivo.")

        # --- Processamento & Geocodificação ---
        lista_processada = []
        for i, (endereco, cep) in enumerate(zip(enderecos, ceps)):
            order_number = order_numbers[i] if i < len(order_numbers) and order_numbers[i] else f"{i+1}"
            res_google = valida_rua_google(endereco, cep)
            novo_item = {
                "order_number": order_number,
                "address": endereco,
                "cep": cep,
                "status_google": res_google.get('status', 'ERRO'),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "importacao_tipo": empresa,
                "cor": cor_por_tipo(empresa),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "endereco_formatado": res_google.get('endereco_formatado', ''),
                "rua_google": res_google.get('route_encontrada', ''),
                "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', '')),
                "freguesia": res_google.get('sublocality', ''),
                "locality": res_google.get('locality', '')
            }
            if registro_unico(lista_processada, novo_item):
                lista_processada.append(novo_item)

        if not lista_processada:
            flash("Nenhum endereço único encontrado após processamento.", "warning")
            return redirect(url_for('preview.home'))

        # Limpa e salva na sessão
        session.clear()
        session['lista'] = lista_processada
        session.modified = True

        flash(f"{len(lista_processada)} endereços importados com sucesso!", "success")
        return redirect(url_for('preview.preview'))

    except Exception as e:
        logger.error(f"[importacao] Erro ao importar: {str(e)}", exc_info=True)
        flash(f"Erro ao importar: {str(e)}", "danger")
        return redirect(url_for('preview.home'))
