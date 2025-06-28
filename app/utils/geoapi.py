# app/utils/geoapi.py

import requests
import os
import re
import logging

GEOAPI_KEY = os.environ.get("GEOAPI_KEY", "SUA_CHAVE_API_GEOAPI")
BASE_URL = "https://json.geoapi.pt"
logger = logging.getLogger(__name__)

def normaliza_nome(s):
    return re.sub(r'[^a-z0-9]', '', s.lower()) if s else ""

def extrai_cep(texto):
    m = re.search(r'(\d{4}-\d{3})', texto)
    return m.group(1) if m else ""

def valida_rua_geoapi(endereco, cep):
    """
    Busca APENAS ruas existentes no CEP. Se não existir, retorna centroide do CEP.
    """
    try:
        partes = [p.strip() for p in re.split(r',', endereco) if p.strip()]
        cep_final = extrai_cep(" ".join(partes)) or cep.replace(" ", "")
        cep_limpo = cep_final.replace("-", "")
        if not cep_limpo or len(cep_limpo) != 7:
            return {"status": "NOT_FOUND", "msg": "Sem CEP válido"}

        rua = partes[0] if partes else endereco.strip()

        # Busca as ruas/artérias do CEP na GeoAPI
        url = f"{BASE_URL}/cp/{cep_limpo}?key={GEOAPI_KEY}"
        resp = requests.get(url, timeout=7)
        if not resp.ok:
            return {"status": "NOT_FOUND", "msg": "CEP não encontrado na base GEOAPI"}
        data = resp.json()
        
        # Tenta matching exato ou "inclusivo" da rua
        arterias = data.get("arterias", [])
        for art in arterias:
            nome_arteria = art.get("arteria", "")
            if normaliza_nome(rua) in normaliza_nome(nome_arteria):
                lat, lng = art.get("coordenadas", [None, None])
                if lat and lng:
                    return {
                        "status": "OK",
                        "coordenadas": {"lat": float(lat), "lng": float(lng)},
                        "postal_code_encontrado": cep_final,
                        "endereco_formatado": f"{nome_arteria}, {cep_final}",
                        "route_encontrada": nome_arteria,
                        "sublocality": "",
                        "locality": art.get("freguesia", ""),
                    }
        
        # Se não achou a rua, retorna centroide do CEP
        centroide = data.get("centroide")
        if centroide:
            lat, lng = map(float, centroide.split(","))
            return {
                "status": "OK_CEP",
                "coordenadas": {"lat": lat, "lng": lng},
                "postal_code_encontrado": cep_final,
                "endereco_formatado": f"{cep_final}",
                "route_encontrada": rua,
                "sublocality": "",
                "locality": "",
            }
        return {"status": "NOT_FOUND", "msg": "Endereço não encontrado na base GEOAPI"}
    except Exception as e:
        logger.exception("Erro na validação geoapi")
        return {"status": "ERRO", "msg": str(e)}
