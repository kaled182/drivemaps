import os

# Importa providers disponíveis
from app.utils.google import valida_rua_google
from app.utils.mapbox import valida_rua_mapbox

GEOCODERS = {
    'google': valida_rua_google,
    'mapbox': valida_rua_mapbox,
    # no futuro: 'tomtom': valida_rua_tomtom, etc.
}

# Define o provider ativo (exemplo: variável de ambiente, config ou banco)
DEFAULT_GEOCODER = os.environ.get("GEOCODER_PROVIDER", "mapbox")

def valida_rua(endereco, cep, provider=None):
    """Função única para validação, redireciona para provider configurado."""
    prov = provider or DEFAULT_GEOCODER
    if prov not in GEOCODERS:
        raise ValueError(f"Geocoder '{prov}' não suportado.")
    return GEOCODERS[prov](endereco, cep)
