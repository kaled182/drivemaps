import requests
import os

def valida_rua_google(endereco, cep=None):
    """
    Valida e geocodifica o endereço usando Google Maps API.
    Retorna lat/lon, endereço formatado, status, e o postal code identificado pelo Google.
    """
    api_key = os.environ.get('GOOGLE_API_KEY')
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    query = endereco
    if cep and cep not in endereco:
        query = f"{endereco}, {cep}, Portugal"
    params = {
        'address': query,
        'region': 'pt',
        'key': api_key
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            return {
                "status": "ERRO_API",
                "endereco_formatado": "",
                "postal_code_encontrado": "",
                "coordenadas": {},
                "detalhe": r.text
            }
        data = r.json()
        if not data.get('results'):
            return {
                "status": "NÃO ENCONTRADO",
                "endereco_formatado": "",
                "postal_code_encontrado": "",
                "coordenadas": {}
            }
        res = data['results'][0]
        componentes = {c['types'][0]: c['long_name'] for c in res['address_components']}
        return {
            "status": "OK",
            "endereco_formatado": res['formatted_address'],
            "coordenadas": res['geometry']['location'],
            "postal_code_encontrado": componentes.get('postal_code', ''),
            "route_encontrada": componentes.get('route', ''),
            "locality": componentes.get('locality', ''),
            "sublocality": componentes.get('sublocality', ''),
        }
    except Exception as e:
        return {
            "status": "ERRO",
            "endereco_formatado": "",
            "postal_code_encontrado": "",
            "coordenadas": {},
            "detalhe": str(e)
        }
