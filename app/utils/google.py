import requests
import os
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

CORES_IMPORTACAO = [
    "#1E90FF",  # Azul padrão
    "#FF8C00",  # Laranja para Paack
    "#32CD32",  # Verde para Delnext
    "#DC143C",  # Vermelho para divergentes
    "#8A2BE2"   # Roxo para manual ou outros
]


@lru_cache(maxsize=1000)
def valida_rua_google(endereco, cep):
    """
    Consulta a API do Google Maps e retorna os dados de geolocalização e
    validação do endereço.
    """
    chave = os.environ.get("GOOGLE_API_KEY")
    if not chave:
        logger.warning(
            "Google API Key não encontrada nas variáveis de "
            "ambiente"
        )
        return {"status": "API_KEY_MISSING"}

    full_address = f"{endereco}, {cep}"
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": full_address,
        "key": chave
    }

    try:
        response = requests.get(url, params=params, timeout=(3, 7))
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {"status": data.get("status", "ZERO_RESULTS")}

        result = data["results"][0]
        endereco_formatado = result.get("formatted_address", "")
        coordenadas = result.get("geometry", {}).get("location", {})
        componentes = result.get("address_components", [])

        retorno = {
            "status": data.get("status", "OK"),
            "endereco_formatado": endereco_formatado,
            "coordenadas": coordenadas,
            "postal_code_encontrado": "",
            "route_encontrada": "",
            "sublocality": ""
        }

        for comp in componentes:
            tipos = comp.get("types", [])
            if "postal_code" in tipos:
                retorno["postal_code_encontrado"] = comp.get("long_name", "")
            elif "route" in tipos:
                retorno["route_encontrada"] = comp.get("long_name", "")
            elif "sublocality" in tipos:
                retorno["sublocality"] = comp.get("long_name", "")

        return retorno

    except requests.Timeout:
        return {"status": "TIMEOUT"}
    except Exception as e:
        logger.exception("Erro na consulta à API do Google Maps")
        return {"status": "ERROR", "msg": str(e)}


# Alias para manter compatibilidade com api.py
valida_rua_google_cache = valida_rua_google
