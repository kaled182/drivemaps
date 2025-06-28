# app/utils/geoapi.py

import requests
import os
import re
import unicodedata

GEOAPI_KEY = os.environ.get("GEOAPI_KEY", "SUA_CHAVE_API_GEOAPI")
BASE_URL = "https://json.geoapi.pt"

def normaliza_nome(s):
    # Remove acentos, espaços, caixa, caracteres especiais
    if not s:
        return ""
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ASCII', 'ignore').decode('utf-8')
    s = re.sub(r'[^a-z0-9]', '', s.lower())
    return s

def valida_rua_geoapi(endereco, cep):
    """
    Busca:
      1. Rua (normalizada) DENTRO DAS RUAS DO CEP
      2. Se não achar, PIN no centroide do CEP
    """
    try:
        # Extrai rua, número (heurística: rua,número,[resto])
        partes = [p.strip() for p in re.split(r',', endereco) if p.strip()]
        rua = partes[0] if partes else endereco.strip()
        numero = ""
        if rua:
            rua_parts = rua.split()
            if rua_parts and rua_parts[-1].isdigit():
                numero = rua_parts[-1]
                rua = " ".join(rua_parts[:-1])
        cep_limpo = cep.replace("-", "").replace(" ", "")
        if not cep_limpo:
            return {"status": "NOT_FOUND", "msg": "Sem CEP para buscar na GeoAPI"}

        # 1. Busca todas as ruas do CEP na GEOAPI
        url_cep = f"{BASE_URL}/cp/{cep_limpo}?key={GEOAPI_KEY}"
        resp = requests.get(url_cep, timeout=6)
        if resp.ok:
            cep_data = resp.json()
            # CEP pode ter 'arterias' (lista de ruas)
            arterias = cep_data.get("arterias", [])
            # Normaliza rua buscada
            rua_norm = normaliza_nome(rua)
            achou_rua = None
            for art in arterias:
                art_nome = art.get("arteria", "")
                if rua_norm in normaliza_nome(art_nome):
                    # Casa a rua!
                    coords = art.get("coordenadas", [None, None])
                    if coords and coords[0] and coords[1]:
                        achou_rua = {
                            "status": "OK",
                            "coordenadas": {"lat": float(coords[0]), "lng": float(coords[1])},
                            "postal_code_encontrado": cep,
                            "endereco_formatado": f"{art_nome} {numero}, {cep}" if numero else f"{art_nome}, {cep}",
                            "route_encontrada": art_nome,
                            "sublocality": art.get("freguesia", ""),
                            "locality": art.get("municipio", ""),
                        }
                        break
            if achou_rua:
                return achou_rua

            # Se não achou, retorna centroide do CEP
            centroide = cep_data.get("centroide")
            if centroide:
                lat, lng = map(float, centroide.split(","))
                return {
                    "status": "OK_CEP",
                    "coordenadas": {"lat": lat, "lng": lng},
                    "postal_code_encontrado": cep,
                    "endereco_formatado": f"{cep}",
                    "route_encontrada": rua,
                    "sublocality": "",
                    "locality": "",
                }
            return {"status": "NOT_FOUND", "msg": f"Não foi possível localizar centroide para o CEP {cep}"}

        return {"status": "NOT_FOUND", "msg": f"CEP {cep} não encontrado na GEOAPI"}
    except Exception as e:
        return {"status": "ERRO", "msg": str(e)}

def obter_endereco_por_coordenadas_geoapi(lat, lng):
    try:
        url = f"{BASE_URL}/gps/{lat},{lng}"
        params = {"key": GEOAPI_KEY}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        d = resp.json()
        if isinstance(d, dict) and d.get("cp4"):
            return {
                "status": "OK",
                "address": d.get("address", ""),
                "postal_code": d.get("cp4", "") + ("-" + d.get("cp3", "") if d.get("cp3") else ""),
                "route_encontrada": d.get("arteria", ""),
                "sublocality": d.get("freguesia", ""),
                "locality": d.get("municipio", ""),
                "coordenadas": {"lat": lat, "lng": lng},
            }
        else:
            return {"status": "NOT_FOUND"}
    except Exception as e:
        return {"status": "ERRO", "msg": str(e)}
