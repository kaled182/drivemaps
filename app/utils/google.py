# app/utils/google.py
"""
Módulo para integração com a Google Maps Geocoding API.
Oferece funções para validação e geolocalização de endereços, e geocodificação reversa.
"""

import requests
import os
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class GoogleAPIError(Exception):
    """Exceção personalizada para erros da API do Google."""
    pass

@lru_cache(maxsize=1000)
def valida_rua_google(endereco: str, cep: str) -> dict:
    """
    Valida e geocodifica um endereço consultando a API do Google Maps.

    Args:
        endereco (str): Endereço (rua, etc)
        cep (str): Código postal (opcional, mas melhora precisão)

    Returns:
        dict: {
            "status": "OK"|"ZERO_RESULTS"|...,
            "endereco_formatado": str,
            "coordenadas": {"lat": float, "lng": float},
            "postal_code_encontrado": str,
            "route_encontrada": str,
            "sublocality": str,
            "locality": str,
            "msg": str (opcional para erros)
        }
    """
    chave = os.environ.get("GOOGLE_API_KEY")
    if not chave:
        logger.warning("Google API Key não encontrada nas variáveis de ambiente")
        return {"status": "API_KEY_MISSING", "msg": "Google API Key não definida."}

    full_address = f"{endereco}, {cep}".strip(", ")
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": full_address,
        "key": chave,
        "language": "pt-PT"
    }

    try:
        response = requests.get(url, params=params, timeout=(3, 7))
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "status": data.get("status", "ZERO_RESULTS"),
                "msg": data.get("error_message", "Nenhum resultado encontrado.")
            }

        result = data["results"][0]
        endereco_formatado = result.get("formatted_address", "")
        coordenadas = result.get("geometry", {}).get("location", {})
        componentes = result.get("address_components", [])

        postal_code = ""
        route = ""
        sublocality = ""
        locality = ""
        for comp in componentes:
            tipos = comp.get("types", [])
            if "postal_code" in tipos and not postal_code:
                postal_code = comp.get("long_name", "")
            elif "route" in tipos and not route:
                route = comp.get("long_name", "")
            elif "sublocality" in tipos and not sublocality:
                sublocality = comp.get("long_name", "")
            elif "locality" in tipos and not locality:
                locality = comp.get("long_name", "")

        return {
            "status": data.get("status", "OK"),
            "endereco_formatado": endereco_formatado,
            "coordenadas": {
                "lat": coordenadas.get("lat"),
                "lng": coordenadas.get("lng")
            } if coordenadas else {},
            "postal_code_encontrado": postal_code,
            "route_encontrada": route,
            "sublocality": sublocality,
            "locality": locality
        }

    except requests.Timeout:
        logger.warning("Timeout na consulta à API do Google Maps.")
        return {"status": "TIMEOUT", "msg": "Tempo de resposta excedido na API Google."}
    except Exception as e:
        logger.exception("Erro inesperado na consulta à API do Google Maps.")
        return {"status": "ERROR", "msg": str(e)}

@lru_cache(maxsize=1000)
def obter_endereco_por_coordenadas(lat, lng) -> dict:
    """
    Faz geocodificação reversa: obtém endereço formatado a partir de coordenadas.

    Args:
        lat (float|str): Latitude
        lng (float|str): Longitude

    Returns:
        dict: {
            "status": "OK"|"ZERO_RESULTS"|...,
            "address": str,
            "postal_code": str,
            "route_encontrada": str,
            "sublocality": str,
            "locality": str,
            "coordenadas": {"lat": float, "lng": float}
        }
    """
    chave = os.environ.get("GOOGLE_API_KEY")
    if not chave:
        logger.warning("Google API Key não encontrada nas variáveis de ambiente")
        return {"status": "API_KEY_MISSING", "msg": "Google API Key não definida."}

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": chave,
        "language": "pt-PT"
    }

    try:
        response = requests.get(url, params=params, timeout=(3, 7))
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "status": data.get("status", "ZERO_RESULTS"),
                "msg": data.get("error_message", "Nenhum resultado encontrado.")
            }

        result = data["results"][0]
        endereco_formatado = result.get("formatted_address", "")
        componentes = result.get("address_components", [])

        postal_code = ""
        route = ""
        sublocality = ""
        locality = ""
        for comp in componentes:
            tipos = comp.get("types", [])
            if "postal_code" in tipos and not postal_code:
                postal_code = comp.get("long_name", "")
            elif "route" in tipos and not route:
                route = comp.get("long_name", "")
            elif "sublocality" in tipos and not sublocality:
                sublocality = comp.get("long_name", "")
            elif "locality" in tipos and not locality:
                locality = comp.get("long_name", "")

        return {
            "status": "OK",
            "address": endereco_formatado,
            "postal_code": postal_code,
            "route_encontrada": route,
            "sublocality": sublocality,
            "locality": locality,
            "coordenadas": {"lat": float(lat), "lng": float(lng)}
        }

    except requests.Timeout:
        logger.warning("Timeout na consulta reversa à API do Google Maps.")
        return {"status": "TIMEOUT", "msg": "Tempo de resposta excedido na API Google."}
    except Exception as e:
        logger.exception("Erro inesperado na consulta reversa à API do Google Maps.")
        return {"status": "ERROR", "msg": str(e)}

# Alias para compatibilidade (usado em várias partes do app)
valida_rua_google_cache = valida_rua_google
