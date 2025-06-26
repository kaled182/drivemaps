# app/utils/mapbox.py

import requests
import os

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "SEU_TOKEN_MAPBOX_AQUI")

def _tenta_busca_cep(cep, params):
    """
    Tenta localizar o centro do CEP no Mapbox, testando com traço, sem traço e só prefixo.
    """
    # Tenta com CEP formatado, limpo e apenas 4 dígitos
    tentativas = [cep, cep.replace("-", ""), cep.split("-")[0]]
    for cep_try in tentativas:
        url_cep = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{cep_try}.json"
        params_cep = dict(params)
        params_cep["types"] = "postcode"
        try:
            r_cep = requests.get(url_cep, params=params_cep)
            r_cep.raise_for_status()
            data_cep = r_cep.json()
            if data_cep.get('features'):
                feat = data_cep['features'][0]
                def get_context(ctx_id):
                    return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")
                return {
                    "status": "OK_CEP_ONLY",
                    "coordenadas": {"lat": feat['center'][1], "lng": feat['center'][0]},
                    "postal_code_encontrado": get_context("postcode"),
                    "endereco_formatado": feat['place_name'],
                    "route_encontrada": "",  # Não encontrou rua, só CEP
                    "sublocality": "",
                    "locality": get_context("place"),
                    "msg": f"Endereço não encontrado, PIN colocado no centro do CEP ({cep_try})."
                }
        except Exception:
            continue
    return {"status": "NOT_FOUND", "msg": "Endereço e CEP não encontrados."}

def valida_rua_mapbox(endereco, cep):
    """
    Valida endereço usando Mapbox Geocoding API.
    Se não encontrar pelo endereço, tenta centralizar o PIN no CEP.
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
            def get_context(ctx_id):
                return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

            return {
                "status": "OK",
                "coordenadas": {"lat": feat['center'][1], "lng": feat['center'][0]},
                "postal_code_encontrado": get_context("postcode"),
                "endereco_formatado": feat['place_name'],
                "route_encontrada": get_context("street"),
                "sublocality": "",
                "locality": get_context("place"),
            }
        elif cep:
            # Tenta achar o centro do CEP
            return _tenta_busca_cep(cep, params)
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
                "postal_code": get_context("postcode"),
                "sublocality": "",
                "locality": get_context("place"),
                "coordenadas": {"lat": lat, "lng": lng},
            }
        else:
            return {"status": "NOT_FOUND"}
    except Exception as e:
        return {"status": "ERRO", "erro": str(e)}
