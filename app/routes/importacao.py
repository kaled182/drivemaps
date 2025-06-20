from flask import Blueprint, request, jsonify, session
import pandas as pd
import re
from app.utils.google import valida_rua_google
from app.utils.helpers import normalizar, registro_unico, cor_por_tipo
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
                df = pd.read_csv(file, header=1)
            else:
                df = pd.read_excel(file, header=1)
            col_end = [c for c in df.columns if 'morada' in c.lower()]
            col_cep = [
                c for c in df.columns
                if 'código postal' in c.lower() or 'codigo postal' in c.lower()
            ]
            if not col_end or not col_cep:
                return jsonify({
                    "success": False,
                    "msg": "Colunas 'Morada' e 'Código Postal' obrigatórias"
                }), 400
            enderecos = df[col_end[0]].astype(str).tolist()
            ceps = df[col_cep[0]].astype(str).tolist()

        elif empresa == "paack":
            file.seek(0)
            if file.filename.lower().endswith(('.csv', '.txt')):
                conteudo = file.read().decode("utf-8")
                linhas = [linha.strip() for linha in conteudo.splitlines() if linha.strip()]
                regex_cep = re.compile(r'(\d{4}-\d{3})')
                i = 0
                # NOVO: Pega sempre blocos de 4 linhas: 1=endereço, 2/3=ignorar, 4=ID
                while i + 3 < len(linhas):
                    endereco = linhas[i]
                    order = linhas[i+3]
                    cep_match = regex_cep.search(endereco)
                    cep = cep_match.group(1) if cep_match else ""
                    enderecos.append(endereco)
                    ceps.append(cep)
                    order_numbers.append(order)
                    i += 4
            else:
                df = pd.read_excel(file, header=0)
                col_end = [
                    c for c in df.columns
                    if 'endereco' in c.lower() or 'address' in c.lower()
                ]
                col_cep = [
                    c for c in df.columns
                    if 'cep' in c.lower() or 'postal' in c.lower()
                ]
                if not col_end or not col_cep:
                    return jsonify({
                        "success": False,
                        "msg": "Colunas de endereço e CEP não encontradas"
                    }), 400
                enderecos = df[col_end[0]].astype(str).tolist()
                ceps = df[col_cep[0]].astype(str).tolist()
                # Se tiver ID do pacote em coluna, acrescente aqui

        else:
            return jsonify({
                "success": False,
                "msg": "Empresa não suportada"
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
