# app/utils/geocoder.py
"""
Módulo "Dispatcher" de Geocodificação.
Decide qual serviço de geocodificação usar, implementando lógica de cascata.
"""

import logging
from . import geoapi   # Para Portugal - preferencial
from . import mapbox   # Fallback 1
from . import google   # Fallback 2

logger = logging.getLogger(__name__)

# Ordem de prioridade dos provedores para busca direta e reversa
GEOCODER_PRIORITY = [
    geoapi.valida_rua_geoapi,
    mapbox.valida_rua_mapbox,
    google.valida_rua_google,
]

REVERSE_GEOCODER_PRIORITY = [
    geoapi.obter_endereco_por_coordenadas_geoapi,
    mapbox.obter_endereco_por_coordenadas,
    google.obter_endereco_por_coordenadas,
]

def valida_rua(endereco: str, cep: str) -> dict:
    """
    Tenta validar um endereço usando provedores em cascata (GeoAPI, Mapbox, Google).
    Retorna o primeiro resultado com status "OK" ou variante.
    """
    logger.info(f"Iniciando validação em cascata para: '{endereco}, {cep}'")
    erros = []
    for geocode_func in GEOCODER_PRIORITY:
        provider_name = geocode_func.__module__.split('.')[-1]
        logger.info(f"Tentando com o provedor: {provider_name}...")
        try:
            resultado = geocode_func(endereco, cep)
            # Aceita status "OK", "OK_CEP", "OK_FREGUESIA", etc
            if resultado and str(resultado.get("status", "")).startswith("OK"):
                logger.info(f"Endereço validado com sucesso via {provider_name}.")
                return resultado
            else:
                logger.warning(f"Provedor {provider_name} falhou ou não encontrou o endereço (Status: {resultado.get('status')}).")
                erros.append({provider_name: resultado})
        except Exception as e:
            logger.error(f"Erro inesperado ao usar o provedor {provider_name}: {e}", exc_info=True)
            erros.append({provider_name: str(e)})
    logger.error(f"Todos os provedores falharam para o endereço: '{endereco}, {cep}'. Retornando falha.")
    return {
        "status": "ALL_PROVIDERS_FAILED",
        "coordenadas": {"lat": 0.0, "lng": 0.0},
        "erros": erros
    }

def obter_endereco_por_coordenadas(lat: float, lng: float) -> dict:
    """
    Tenta obter um endereço a partir de coordenadas usando provedores em cascata.
    Retorna o primeiro resultado com status "OK" ou variante.
    """
    logger.info(f"Iniciando geocodificação reversa em cascata para: lat={lat}, lng={lng}")
    erros = []
    for reverse_geocode_func in REVERSE_GEOCODER_PRIORITY:
        provider_name = reverse_geocode_func.__module__.split('.')[-1]
        logger.info(f"Tentando geocodificação reversa com o provedor: {provider_name}...")
        try:
            resultado = reverse_geocode_func(lat, lng)
            if resultado and str(resultado.get("status", "")).startswith("OK"):
                logger.info(f"Endereço reverso encontrado com sucesso via {provider_name}.")
                return resultado
            else:
                logger.warning(f"Provedor {provider_name} falhou na busca reversa (Status: {resultado.get('status')}).")
                erros.append({provider_name: resultado})
        except Exception as e:
            logger.error(f"Erro inesperado na busca reversa com o provedor {provider_name}: {e}", exc_info=True)
            erros.append({provider_name: str(e)})
    logger.error(f"Todos os provedores falharam na busca reversa para: lat={lat}, lng={lng}.")
    return {
        "status": "ALL_PROVIDERS_FAILED",
        "address": "Não foi possível encontrar o endereço.",
        "erros": erros
    }
