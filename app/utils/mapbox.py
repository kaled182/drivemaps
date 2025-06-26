import requests
import os

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "SEU_TOKEN_MAPBOX")

def valida_rua_mapbox(endereco, cep):
    """Valida endereço usando Mapbox Geocoding API."""
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
        if data['features']:
            feat = data['features'][0]
            # Ajuste os campos conforme seu padrão de retorno
            return {
                "status": "OK",
                "coordenadas": {"lat": feat['center'][1], "lng": feat['center'][0]},
                "postal_code_encontrado": next((c['text'] for c in feat.get('context', []) if c['id'].startswith('postcode')), ""),
                "endereco_formatado": feat['place_name'],
                "route_encontrada": next((c['text'] for c in feat.get('context', []) if c['id'].startswith('street')), ""),
                "sublocality": "",
                "locality": next((c['text'] for c in feat.get('context', []) if c['id'].startswith('place')), ""),
            }
        else:
            return {"status": "NOT_FOUND"}
    except Exception as e:
        return {"status": "ERRO", "erro": str(e)}
