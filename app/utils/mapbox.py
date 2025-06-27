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
    Busca SEMPRE nesta ordem:
    1. CEP + endereço/número
    2. CEP apenas
    3. Endereço apenas
    Se tudo falhar, retorna centro do país para garantir exibição do PIN.
    """
    # 1. Busca: CEP + Endereço
    consulta = f"{endereco}, {cep}" if cep else endereco
    features = _busca_geocode_mapbox(consulta)
    
    # 2. Se não achou, tenta só o CEP
    if not features and cep:
        features = _busca_geocode_mapbox(cep)
    
    # 3. Se não achou, tenta só o endereço
    if not features and endereco:
        features = _busca_geocode_mapbox(endereco)
    
    # 4. Fallback: Centro de Portugal continental
    if not features:
        return {
            "status": "NOT_FOUND",
            "coordenadas": {"lat": 39.3999, "lng": -8.2245},  # Já são float
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
        # Garante que as coordenadas são sempre float
        "coordenadas": {
            "lat": float(feat['center'][1]), 
            "lng": float(feat['center'][0])
        },
        "postal_code_encontrado": get_context("postcode"),
        "endereco_formatado": feat['place_name'],
        "route_encontrada": get_context("street"),
        "sublocality": "",
        "locality": get_context("place"),
    }

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
        r = requests.get(url, params=params, timeout=7)
        r.raise_for_status()
        data = r.json()
        if data.get('features'):
            feat = data['features'][0]
            def get_context(ctx_id):
                return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

            return {
                "status": "OK",
                "address": feat['place_name'],
                "postal_code": get_context("postcode"),
                "sublocality": "",
                "locality": get_context("place"),
                "coordenadas": {"lat": float(lat), "lng": float(lng)},
            }
        # Em caso de não encontrar, retorna um status claro mas mantém as coordenadas
        return {
            "status": "NOT_FOUND",
            "address": "Endereço não encontrado",
            "postal_code": "",
            "coordenadas": {"lat": float(lat), "lng": float(lng)}
        }
    except Exception as e:
        return {
            "status": "ERRO",
            "address": f"Erro na API: {e}",
            "postal_code": "",
            "coordenadas": {"lat": float(lat), "lng": float(lng)}
        }
