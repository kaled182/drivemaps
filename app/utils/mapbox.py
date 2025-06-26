# app/utils/mapbox.py

import requests
import os

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "SEU_TOKEN_MAPBOX_AQUI")

def valida_rua_mapbox(endereco, cep):
    """
    Valida endereço usando Mapbox Geocoding API.
    """
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
            # Encontra informações nos contextos
            def get_context(ctx_id):
                return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

            return {
                "status": "OK",
                "coordenadas": {"lat": feat['center'][1], "lng": feat['center'][0]},
                "postal_code_encontrado": get_context("postcode"),
                "endereco_formatado": feat['place_name'],
                "route_encontrada": get_context("street"),
                "sublocality": "",  # Mapbox não retorna sublocality explícito
                "locality": get_context("place"),
            }
        else:
            return {"status": "NOT_FOUND"}
    except Exception as e:
        return {"status": "ERRO", "erro": str(e)}
