from flask import Blueprint, render_template, request, session, jsonify
from app.utils.google import valida_rua_google
from app.utils.helpers import normalizar, registro_unico, CORES_IMPORTACAO
from app.utils import parser
import os
import logging

preview_bp = Blueprint('preview', __name__)

@preview_bp.route("/", methods=["GET"], endpoint="home")
def index():
    return render_template("index.html")

@preview_bp.route('/preview', methods=['POST'])
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

        enderecos, ceps, order_numbers = parser.parse_paack(enderecos_brutos)

        logging.warning(f"[preview] Entradas extraídas: {len(enderecos)} endereços, {len(ceps)} ceps, {len(order_numbers)} ids")
        logging.warning(f"[preview] Dados exemplo: {enderecos[:2]}, {ceps[:2]}, {order_numbers[:2]}")

        if not enderecos:
            raise ValueError("Nenhum endereço extraído do texto fornecido. Verifique o formato de entrada (mínimo 4 linhas por pacote Paack).")

        importacao_tipo = "paack"
        lista_preview = []
        for endereco, cep, numero_pacote in zip(enderecos, ceps, order_numbers):
            res_google = valida_rua_google(endereco, cep)
            rua_digitada = endereco.split(',')[0] if endereco else ''
            rua_google = res_google.get('route_encontrada', '')
            rua_bate = (
                normalizar(rua_digitada) in normalizar(rua_google)
                or normalizar(rua_google) in normalizar(rua_digitada)
            )
            cep_ok = cep == res_google.get('postal_code_encontrado', '')
            lista_preview.append({
                "order_number": numero_pacote,
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
                "importacao_tipo": importacao_tipo,
                "cor": CORES_IMPORTACAO.get(importacao_tipo, "#4285F4")
            })

        lista_atual = session.get('lista', [])
        for novo in lista_preview:
            if registro_unico(lista_atual, novo):
                lista_atual.append(novo)

        # Renumera todos para garantir sequência
        for i, item in enumerate(lista_atual, 1):
            item['order_number'] = i

        session['lista'] = lista_atual
        session.modified = True

        # Aqui só enviamos o MAPBOX_TOKEN para o template (Google API Key não é mais necessária)
        return render_template(
            "preview.html",
            lista=lista_atual,
            MAPBOX_TOKEN=os.environ.get("MAPBOX_TOKEN", ""),
            CORES_IMPORTACAO=CORES_IMPORTACAO,
            origens=list({
                item.get('importacao_tipo', 'manual')
                for item in lista_atual
            })
        )

    except Exception as e:
        logging.error(f"[preview] Erro ao processar preview: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": str(e)}), 500
