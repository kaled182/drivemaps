import requests
import time

def get_lat_lng(address, api_key, delay=0.1):
    """
    Retorna (lat, lng) para um endereço usando a API do Google Maps.
    Retorna (None, None) se não encontrar ou em caso de erro.

    :param address: Endereço completo como string
    :param api_key: Chave de API do Google Maps
    :param delay: Tempo (em segundos) para aguardar entre requisições (evita rate limit)
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("status") == "OK":
            location = data["results"][0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
            if delay:
                time.sleep(delay)
            return lat, lng
    except Exception as e:
        print(f"Erro ao geocodificar '{address}': {e}")
    return None, None
