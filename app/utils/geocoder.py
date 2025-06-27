# app/utils/geocoder.py
"""
Módulo "Dispatcher" de Geocodificação.
Decide qual serviço de geocodificação usar, implementando uma lógica de cascata
para máxima precisão e robustez.
"""
import logging
from . import geoapi   # (Mais preciso para PT)
from . import mapbox   # (Fallback 1)
from . import google   # (Fallback 2)

logger = logging.getLogger(__name__)

# Define a ordem de prioridade para os provedores de geocodificação.
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
    Tenta validar um endereço usando uma hierarquia de serviços para obter a melhor resposta.
    Ordem: GeoAPI.pt -> Mapbox -> Google Maps.
    """
    logger.info(f"Iniciando validação em cascata para: '{endereco}, {cep}'")
    
    for geocode_func in GEOCODER_PRIORITY:
        provider_name = geocode_func.__module__.split('.')[-1]
        logger.info(f"Tentando com o provedor: {provider_name}...")
        try:
            resultado = geocode_func(endereco, cep)
            # Se o resultado for bem-sucedido, retorna-o imediatamente.
            if resultado and resultado.get("status") == "OK":
                logger.info(f"Endereço validado com sucesso via {provider_name}.")
                return resultado
            else:
                logger.warning(f"Provedor {provider_name} falhou ou não encontrou o endereço (Status: {resultado.get('status')}).")
        except Exception as e:
            logger.error(f"Erro inesperado ao usar o provedor {provider_name}: {e}", exc_info=True)

    logger.error(f"Todos os provedores falharam para o endereço: '{endereco}, {cep}'. Retornando falha.")
    # Retorna uma resposta de falha padronizada se todos os provedores falharem.
    return {"status": "ALL_PROVIDERS_FAILED", "coordenadas": {"lat": 0.0, "lng": 0.0}}


def obter_endereco_por_coordenadas(lat: float, lng: float) -> dict:
    """
    Tenta obter um endereço a partir de coordenadas usando a hierarquia de serviços.
    Ordem: GeoAPI.pt -> Mapbox -> Google Maps.
    """
    logger.info(f"Iniciando geocodificação reversa em cascata para: lat={lat}, lng={lng}")

    for reverse_geocode_func in REVERSE_GEOCODER_PRIORITY:
        provider_name = reverse_geocode_func.__module__.split('.')[-1]
        logger.info(f"Tentando geocodificação reversa com o provedor: {provider_name}...")
        try:
            resultado = reverse_geocode_func(lat, lng)
            if resultado and resultado.get("status") == "OK":
                logger.info(f"Endereço reverso encontrado com sucesso via {provider_name}.")
                return resultado
            else:
                logger.warning(f"Provedor {provider_name} falhou na busca reversa (Status: {resultado.get('status')}).")
        except Exception as e:
            logger.error(f"Erro inesperado na busca reversa com o provedor {provider_name}: {e}", exc_info=True)

    logger.error(f"Todos os provedores falharam na busca reversa para: lat={lat}, lng={lng}.")
    return {"status": "ALL_PROVIDERS_FAILED", "address": "Não foi possível encontrar o endereço."}
