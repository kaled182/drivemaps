from flask import Blueprint, request, jsonify, session
import pandas as pd
from app.utils.google import valida_rua_google
from app.utils.helpers import normalizar, registro_unico, cor_por_tipo
from app.utils import parser   # <<< NOVO: importa o parser centralizado
import logging

logger = logging.getLogger(__name__)
importacao_bp = Blueprint('importacao', __name__)

ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'txt'}

def extensao_permitida(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@importacao_bp.route('/import_planilha', methods=['POST'])
def import_planilha():
    try:
        file = request.files.get('planilha')
        empresa = request.form.get('empresa', '').lower()

        if not file or not empresa:
            return jsonify({
                "success": False,
                "msg": "Arquivo ou empresa não especificados"
            }), 400

        if not extensao_permitida(file.filename):
            return jsonify({
                "success": False,
                "msg": "Tipo de arquivo não permitido"
            }), 400

        logger.info(f"Importação iniciada para empresa: {empresa}")
        tipo_import = empresa
        enderecos, ceps, order_numbers = [], [], []

        if empresa == "delnext":
            file.seek(0)
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            enderecos, ceps, order_numbers = parser.parse_delnext(df)

        elif empresa == "paack":
            file.seek(0)
            if file.filename.lower().endswith(('.csv', '.txt')):
                conteudo = file.read().decode("utf-8")
                enderecos, ceps, order_numbers = parser.parse_paack(conteudo)
            else:
                df = pd.read_excel(file)
                # Se algum dia Paack aceitar xlsx estruturado, pode criar parser.parse_paack_xlsx(df)
                # Por enquanto: não implementado, mas não quebra
                enderecos, ceps, order_numbers = [], [], []

        else:
            return jsonify({
                "success": False,
                "msg": "Empresa não suportada"
            }), 400

        if not enderecos:
            return jsonify({
                "success": False,
                "msg": "Não foi possível identificar endereços na planilha enviada."
            }), 400

        if not order_numbers:
            order_numbers = [str(i + 1) for i in range(len(enderecos))]

        lista_atual = session.get('lista', [])

        for endereco, cep, order_number in zip(enderecos, ceps, order_numbers):
            res_google = valida_rua_google(endereco, cep)
            rua_digitada = endereco.split(',')[0] if endereco else ''
            rua_google = res_google.get('route_encontrada', '')
            rua_bate = (
                normalizar(rua_digitada) in normalizar(rua_google)
                or normalizar(rua_google) in normalizar(rua_digitada)
            )
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
                "cor": cor_por_tipo(tipo_import)
            }

            if registro_unico(lista_atual, novo):
                lista_atual.append(novo)

        for i, item in enumerate(lista_atual, 1):
            item['order_number'] = i

        session['lista'] = lista_atual
        session.modified = True

        return jsonify({
            "success": True,
            "lista": lista_atual,
            "origens": list({
                item.get('importacao_tipo', 'manual')
                for item in lista_atual
            }),
            "total": len(lista_atual)
        })

    except Exception as e:
        logger.error(f"Erro na importação: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "msg": f"Erro ao importar: {str(e)}"
        }), 500
