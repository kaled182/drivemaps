# app/utils/geocoder.py

import os
from app.utils.google import valida_rua_google
from app.utils.mapbox import valida_rua_mapbox

GEOCODERS = {
    "google": valida_rua_google,
    "mapbox": valida_rua_mapbox,
    # No futuro: "tomtom": valida_rua_tomtom, etc.
}

DEFAULT_GEOCODER = os.environ.get("GEOCODER_PROVIDER", "mapbox")

def valida_rua(endereco, cep, provider=None):
    """
    Faz a validação de endereço usando o provider configurado (Google, Mapbox, ...).
    """
    prov = provider or DEFAULT_GEOCODER
    if prov not in GEOCODERS:
        raise ValueError(f"Geocoder '{prov}' não suportado.")
    return GEOCODERS[prov](endereco, cep)
