# app/utils/geocoder.py

import os
from app.utils.google import (
    valida_rua_google,
    obter_endereco_por_coordenadas as google_reverse
)
from app.utils.mapbox import (
    valida_rua_mapbox,
    obter_endereco_por_coordenadas as mapbox_reverse
)

GEOCODERS = {
    "google": valida_rua_google,
    "mapbox": valida_rua_mapbox,
    # No futuro: "tomtom": valida_rua_tomtom, etc.
}

REVERSE_GEOCODERS = {
    "google": google_reverse,
    "mapbox": mapbox_reverse,
    # No futuro: "tomtom": tomtom_reverse, etc.
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

def obter_endereco_por_coordenadas(lat, lng, provider=None):
    """
    Faz a busca reversa de coordenadas para endereço usando o provider configurado.
    """
    prov = provider or DEFAULT_GEOCODER
    if prov not in REVERSE_GEOCODERS:
        raise ValueError(f"Reverse geocoder '{prov}' não suportado.")
    return REVERSE_GEOCODERS[prov](lat, lng)
