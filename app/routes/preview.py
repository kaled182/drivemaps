from flask import Blueprint, render_template, request, session, jsonify
from app.utils.google import valida_rua_google
from app.utils.helpers import normalizar, registro_unico, CORES_IMPORTACAO
import os
import re

preview_bp = Blueprint('preview', __name__)


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

        regex_cep = r'(\d{4}-\d{3})'
        linhas = [
            linha.strip()
            for linha in enderecos_brutos.split('\n')
            if linha.strip()
        ]
        lista_preview = []
        i = 0
        while i < len(linhas) - 2:
            linha = linhas[i]
            if i + 2 < len(linhas) and linhas[i+2] == linha:
                numero_pacote = linhas[i+3] if (i+3) < len(linhas) else ""
                cep_match = re.search(regex_cep, linha)
                cep = cep_match.group(1) if cep_match else ''
                res_google = valida_rua_google(linha, cep)
                rua_digitada = linha.split(',')[0] if linha else ''
                rua_google = res_google.get('route_encontrada', '')
                rua_bate = (
                    normalizar(rua_digitada) in normalizar(rua_google)
                    or normalizar(rua_google) in normalizar(rua_digitada)
                )
                cep_ok = cep == res_google.get('postal_code_encontrado', '')
                lista_preview.append({
                    "order_number": numero_pacote,
                    "address": linha,
                    "cep": cep,
                    "status_google": res_google.get('status'),
                    "postal_code_encontrado": res_google.get(
                        'postal_code_encontrado', ''
                    ),
                    "endereco_formatado": res_google.get(
                        'endereco_formatado', ''
                    ),
                    "latitude": res_google.get(
                        'coordenadas', {}
                    ).get('lat', ''),
                    "longitude": res_google.get(
                        'coordenadas', {}
                    ).get('lng', ''),
                    "rua_google": rua_google,
                    "cep_ok": cep_ok,
                    "rua_bate": rua_bate,
                    "freguesia": res_google.get('sublocality', ''),
                    "importacao_tipo": "manual",
                    "cor": CORES_IMPORTACAO[0]
                })
                i += 4
            else:
                i += 1

        lista_atual = session.get('lista', [])
        for novo in lista_preview:
            if registro_unico(lista_atual, novo):
                lista_atual.append(novo)

        for i, item in enumerate(lista_atual, 1):
            item['order_number'] = i

        session['lista'] = lista_atual
        session.modified = True

        return render_template(
            "preview.html",
            lista=lista_atual,
            GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
            CORES_IMPORTACAO=CORES_IMPORTACAO,
            origens=list({
                item.get('importacao_tipo', 'manual')
                for item in lista_atual
            })
        )

    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500
