# app/utils/mapbox.py

import requests
import os

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "SEU_TOKEN_MAPBOX_AQUI")

def valida_rua_mapbox(endereco, cep):
    """
    Valida endereço usando Mapbox Geocoding API.
    Se não encontrar, tenta posicionar o PIN dentro do CEP informado.
    """
    def get_context(ctx_id, feat):
        return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

    # 1. Primeira tentativa: endereço completo
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{endereco}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "country": "PT",
        "limit": 1
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if data.get('features'):
            feat = data['features'][0]
            return {
                "status": "OK",
                "coordenadas": {"lat": feat['center'][1], "lng": feat['center'][0]},
                "postal_code_encontrado": get_context("postcode", feat),
                "endereco_formatado": feat['place_name'],
                "route_encontrada": get_context("street", feat),
                "sublocality": "",
                "locality": get_context("place", feat),
            }
        # Se não encontrou o endereço, tenta pelo CEP
        elif cep:
            # 2. Segunda tentativa: busca por CEP
            url_cep = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{cep}.json"
            r_cep = requests.get(url_cep, params=params)
            r_cep.raise_for_status()
            data_cep = r_cep.json()
            if data_cep.get('features'):
                feat = data_cep['features'][0]
                return {
                    "status": "OK_CEP_ONLY",
                    "coordenadas": {"lat": feat['center'][1], "lng": feat['center'][0]},
                    "postal_code_encontrado": get_context("postcode", feat),
                    "endereco_formatado": feat['place_name'],
                    "route_encontrada": "",  # Não encontrou rua, só CEP
                    "sublocality": "",
                    "locality": get_context("place", feat),
                    "msg": "Endereço não encontrado, PIN colocado no centro do CEP."
                }
            else:
                return {"status": "NOT_FOUND", "msg": "Endereço e CEP não encontrados."}
        else:
            return {"status": "NOT_FOUND", "msg": "Endereço não encontrado e CEP não fornecido."}
    except Exception as e:
        return {"status": "ERRO", "erro": str(e)}

def obter_endereco_por_coordenadas(lat, lng):
    """
    Busca reversa de endereço (coordenadas para endereço) usando Mapbox Geocoding API.
    """
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "country": "PT",
        "limit": 1
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if data.get('features'):
            feat = data['features'][0]
            def get_context(ctx_id):
                return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

            return {
                "status": "OK",
                "address": feat['place_name'],
                "postal_code": get_context("postcode", feat),
                "sublocality": "",
                "locality": get_context("place", feat),
                "coordenadas": {"lat": lat, "lng": lng},
            }
        else:
            return {"status": "NOT_FOUND"}
    except Exception as e:
        return {"status": "ERRO", "erro": str(e)}
