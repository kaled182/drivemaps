# app/routes/api.py
from flask import Blueprint, request, jsonify, session
from app.utils.google import valida_rua_google_cache
from app.utils.helpers import normalizar
import logging

api_routes = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    try:
        data = request.get_json()
        idx = data.get('idx')
        endereco = data.get('endereco', '')
        cep = data.get('cep', '')
        tipo = data.get('importacao_tipo', 'manual')
        numero = data.get('numero_pacote', str(idx + 1 if idx is not None else 0))

        resultado = valida_rua_google_cache(endereco, cep)
        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = resultado.get('route_encontrada', '')
        cep_ok = cep == resultado.get('postal_code_encontrado', '')
        rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)

        cor = {
            'manual': "#0074D9",
            'delnext': "#FF851B",
            'paack': "#2ECC40"
        }.get(tipo, "#B10DC9")

        novo = {
            "order_number": numero,
            "address": endereco,
            "cep": cep,
            "status_google": resultado.get('status'),
            "postal_code_encontrado": resultado.get('postal_code_encontrado', ''),
            "endereco_formatado": resultado.get('endereco_formatado', ''),
            "latitude": resultado.get('coordenadas', {}).get('lat'),
            "longitude": resultado.get('coordenadas', {}).get('lng'),
            "rua_google": rua_google,
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "freguesia": resultado.get('sublocality', ''),
            "importacao_tipo": tipo,
            "cor": cor
        }

        lista = session.get('lista', [])
        if idx is not None and 0 <= idx < len(lista):
            lista[idx] = novo
        else:
            lista.append(novo)

        session['lista'] = lista
        session.modified = True

        return jsonify({
            "success": True,
            "item": novo,
            "idx": idx if idx is not None else len(lista) - 1
        })
    except Exception as e:
        logger.error(f"Erro ao validar linha: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": str(e)}), 500


@api_routes.route('/api/session-data', methods=['GET'])
def session_data():
    lista = session.get('lista', [])
    return jsonify({
        "success": True,
        "lista": lista,
        "total": len(lista),
        "origens": list({item.get("importacao_tipo", "manual") for item in lista})
    })


@api_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        idx = data.get('idx')
        lat = data.get('lat')
        lng = data.get('lng')

        if None in [idx, lat, lng]:
            return jsonify({'success': False, 'msg': 'Dados incompletos'}), 400

        import requests
        import os
        api_key = os.getenv("GOOGLE_API_KEY", "")
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": f"{lat},{lng}",
            "key": api_key
        }

        r = requests.get(url, params=params, timeout=(3, 7))
        r.raise_for_status()
        data_json = r.json()

        if not data_json.get('results'):
            return jsonify({"success": False, "msg": "Endereço não encontrado"}), 404

        result = data_json['results'][0]
        address = result.get('formatted_address', '')
        postal_code = ''
        for comp in result.get('address_components', []):
            if 'postal_code' in comp.get('types', []):
                postal_code = comp.get('long_name')
                break

        lista = session.get('lista', [])
        if 0 <= idx < len(lista):
            lista[idx].update({
                "latitude": lat,
                "longitude": lng
            })
            session['lista'] = lista
            session.modified = True

        return jsonify({
            "success": True,
            "address": address,
            "cep": postal_code
        })

    except requests.Timeout:
        return jsonify({'success': False, 'msg': 'Timeout ao conectar com o Google Maps'}), 504
    except Exception as e:
        logger.error(f"Erro no reverse-geocode: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'msg': str(e)}), 500
