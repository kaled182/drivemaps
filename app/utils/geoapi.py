# app/utils/geoapi.py
"""
Módulo para interação com a GeoAPI.pt, especializada em geocodificação para Portugal.
"""
import requests
import os
import logging

logger = logging.getLogger(__name__)

# A sua chave da API deve ser configurada como uma variável de ambiente no seu servidor (Render).
GEOAPI_KEY = os.environ.get("GEOAPI_KEY")

def _make_request(url: str, params: dict) -> dict:
    """Função auxiliar para fazer requisições à GeoAPI."""
    if not GEOAPI_KEY:
        logger.warning("GEOAPI_KEY não está configurada. Saltando a busca na GeoAPI.pt.")
        return {}
    
    params['key'] = GEOAPI_KEY
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()  # Lança exceção para erros HTTP (4xx ou 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao comunicar com a GeoAPI.pt: {e}")
        return {}

def valida_rua_geoapi(endereco: str, cep: str) -> dict:
    """
    Valida um endereço usando a GeoAPI.pt, que é mais precisa para Portugal.
    Retorna um dicionário padronizado.
    """
    # A GeoAPI funciona melhor com consultas combinadas.
    query = f"{endereco} {cep}".strip()
    if not query:
        return {"status": "INVALID_QUERY"}

    data = _make_request("https://geoapi.pt/v3/search", {"q": query, "limit": 1})
    
    if not data or not isinstance(data, list) or len(data) == 0:
        return {"status": "NOT_FOUND"}

    result = data[0]
    coords = result.get("centro")

    # Garante que as coordenadas são floats válidos
    try:
        lat = float(coords.get("lat"))
        lng = float(coords.get("lon"))
    except (ValueError, TypeError):
        return {"status": "INVALID_COORDS"}

    return {
        "status": "OK",
        "coordenadas": {"lat": lat, "lng": lng},
        "postal_code_encontrado": result.get("cod_postal", ""),
        "endereco_formatado": result.get("morada", endereco),
        "route_encontrada": result.get("rua", ""),
        "sublocality": result.get("freguesia", ""),
        "locality": result.get("concelho", ""),
        "source": "GeoAPI.pt" # Adiciona a fonte para depuração
    }

def obter_endereco_por_coordenadas_geoapi(lat: float, lng: float) -> dict:
    """
    Busca reversa de endereço usando a GeoAPI.pt.
    """
    params = {"lat": lat, "lon": lng}
    data = _make_request("https://geoapi.pt/v3/reverse", params)

    if not data or not isinstance(data, list) or len(data) == 0:
        return {"status": "NOT_FOUND"}
    
    result = data[0]
    return {
        "status": "OK",
        "address": result.get("morada", "Endereço não encontrado"),
        "postal_code": result.get("cod_postal", ""),
        "sublocality": result.get("freguesia", ""),
        "locality": result.get("concelho", ""),
        "coordenadas": {"lat": lat, "lng": lng},
        "source": "GeoAPI.pt"
    }
