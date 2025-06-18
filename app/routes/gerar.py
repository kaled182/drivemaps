import requests
import os
import logging

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

CORES_IMPORTACAO = [
    "#1E90FF",  # Azul padrão
    "#FF8C00",  # Laranja para Paack
    "#32CD32",  # Verde para Delnext
    "#DC143C",  # Vermelho para divergentes
    "#8A2BE2"   # Roxo para manual ou outros
]

def valida_rua_google(endereco, cep=None):
    try:
        if not GOOGLE_MAPS_API_KEY:
            raise ValueError("Google Maps API Key não configurada")

        endereco_completo = f"{endereco}, Portugal" if "Portugal" not in endereco else endereco
        if cep:
            endereco_completo = f"{endereco_completo}, {cep}"

        response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={'address': endereco_completo, 'key': GOOGLE_MAPS_API_KEY}
        )

        if response.status_code != 200:
            raise Exception(f"Erro HTTP: {response.status_code}")

        data = response.json()
        if not data.get("results"):
            return {"status": "ZERO_RESULTS"}

        resultado = data["results"][0]
        endereco_formatado = resultado.get("formatted_address", "")
        coordenadas = resultado.get("geometry", {}).get("location", {})

        route = ""
        postal_code = ""
        sublocality = ""

        for comp in resultado.get("address_components", []):
            if "route" in comp["types"]:
                route = comp["long_name"]
            if "postal_code" in comp["types"]:
                postal_code = comp["long_name"]
            if "sublocality" in comp["types"] or "sublocality_level_1" in comp["types"]:
                sublocality = comp["long_name"]

        return {
            "status": data.get("status", "OK"),
            "endereco_formatado": endereco_formatado,
            "coordenadas": coordenadas,
            "route_encontrada": route,
            "postal_code_encontrado": postal_code,
            "sublocality": sublocality
        }

    except Exception as e:
        logger.error(f"Erro na validação do endereço: {str(e)}", exc_info=True)
        return {"status": "ERROR", "erro": str(e)}
