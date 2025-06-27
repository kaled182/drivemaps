# app/utils/mapbox.py

import requests
import os

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "SEU_TOKEN_MAPBOX_AQUI")

def _busca_geocode_mapbox(query):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "country": "PT",
        "limit": 1
    }
    try:
        r = requests.get(url, params=params, timeout=7)
        r.raise_for_status()
        data = r.json()
        return data.get('features', [])
    except Exception as e:
        return []

def valida_rua_mapbox(endereco, cep):
    """
    Busca o endereço na API do Mapbox, usando as estratégias:
      1. endereço + cep
      2. somente cep
      3. somente endereço
    Sempre retorna lat/lng como float.
    """
    consulta = f"{endereco}, {cep}" if cep else endereco
    features = _busca_geocode_mapbox(consulta)

    if not features and cep:
        features = _busca_geocode_mapbox(cep)
    
    if not features and endereco:
        features = _busca_geocode_mapbox(endereco)

    # Não encontrou nada? Retorno padrão.
    if not features:
        return {
            "status": "NOT_FOUND",
            "coordenadas": {"lat": 39.3999, "lng": -8.2245},  # Centro PT
            "postal_code_encontrado": "",
            "endereco_formatado": "Endereço não encontrado",
            "route_encontrada": "",
            "sublocality": "",
            "locality": ""
        }

    feat = features[0]
    def get_context(ctx_id):
        return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

    return {
        "status": "OK",
        "coordenadas": {
            "lat": float(feat['center'][1]),
            "lng": float(feat['center'][0])
        },
        "postal_code_encontrado": get_context("postcode"),
        "endereco_formatado": feat.get('place_name', ''),
        "route_encontrada": get_context("street"),
        "sublocality": "",
        "locality": get_context("place"),
    }

def obter_endereco_por_coordenadas(lat, lng):
    """
    Busca reversa de endereço a partir de coordenadas (Mapbox).
    Sempre retorna lat/lng como float.
    """
    lat, lng = float(lat), float(lng)
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "country": "PT",
        "limit": 1
    }
    try:
        r = requests.get(url, params=params, timeout=7)
        r.raise_for_status()
        data = r.json()
        if data.get('features'):
            feat = data['features'][0]
            def get_context(ctx_id):
                return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

            return {
                "status": "OK",
                "address": feat.get('place_name', ''),
                "postal_code": get_context("postcode"),
                "route_encontrada": get_context("street"),
                "sublocality": "",
                "locality": get_context("place"),
                "coordenadas": {"lat": lat, "lng": lng}
            }
        return {
            "status": "NOT_FOUND",
            "address": "Endereço não encontrado",
            "coordenadas": {"lat": lat, "lng": lng}
        }
    except Exception as e:
        return {
            "status": "ERRO",
            "address": f"Erro na API: {e}",
            "coordenadas": {"lat": lat, "lng": lng}
        }
